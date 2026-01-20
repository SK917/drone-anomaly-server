import asyncio
import json
import time
import uuid
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import torch
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.sdp import candidate_from_sdp
from ultralytics import YOLO
from ultralytics.trackers import BYTETracker

# Suppress FFmpeg decoder errors
os.environ["AV_LOG_FORCE_NOCOLOR"] = "1"
os.environ["AV_LOG_LEVEL"] = "fatal"
os.environ["OPENCV_LOG_LEVEL"] = "FATAL"

import warnings
warnings.filterwarnings('ignore')

# =========================
# CONFIG
# =========================
HOST = "0.0.0.0"
PORT = 8000

MODEL_PATH = "yolo11s.pt"
INFERENCE_SIZE = 512
CONFIDENCE_THRESHOLD = 0.25
USE_FP16 = True

DETECTIONS_JSON_PATH = "latest_detections/detections.json"

# Browser MJPEG (keep low to avoid RAM/CPU spikes)
STREAM_FPS = 12
STREAM_MAX_WIDTH = 960
JPEG_QUALITY = 85

# Inference throttling
MIN_INFERENCE_INTERVAL = 0.12  # ~8Hz

# =========================
# GLOBAL STATE
# =========================
pcs: Dict[str, RTCPeerConnection] = {}

# Simple frame storage (no locks needed with single writer)
latest_frame: Optional[np.ndarray] = None
latest_frame_ts: float = 0.0

latest_jpeg_bytes: Optional[bytes] = None
latest_jpeg_lock = asyncio.Lock()

latest_result: Optional[Dict[str, Any]] = None
latest_result_lock = asyncio.Lock()

capture_fps: float = 0.0
_last_cap_count = 0
_last_cap_t0 = time.time()

inference_count = 0
inference_start_time: Optional[float] = None
last_inference_time_ms: float = 0.0

model: Optional[YOLO] = None
device: str = "cpu"
tracker: Optional[BYTETracker] = None

# Anomaly detection
backpack_detected: bool = False
backpack_detection_lock = asyncio.Lock()

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4)
processing_frame = False


# =========================
# UTIL
# =========================
def save_detections_json(detections_dict: Dict[str, Any]) -> None:
    try:
        p = Path(DETECTIONS_JSON_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(detections_dict, indent=2))
    except Exception:
        pass


def make_detections_from_results(results) -> Tuple[List[Dict[str, Any]], bool]:
    dets: List[Dict[str, Any]] = []
    backpack_found = False
    if results is None:
        return dets, backpack_found
    for result in results:
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            try:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                bbox = box.xyxy[0].tolist()
                class_name = result.names[cls_id] if hasattr(result, "names") else str(cls_id)
                
                # Check for person (class_id 0 in COCO dataset)
                if class_name.lower() == "person":
                    backpack_found = True
                
                # Get track_id if available
                track_id = None
                if hasattr(box, "id") and box.id is not None:
                    track_id = int(box.id[0])
                
                dets.append({
                    "class_id": cls_id,
                    "class_name": class_name,
                    "confidence": conf,
                    "bbox": bbox,
                    "track_id": track_id,
                    "is_backpack": class_name.lower() == "person",
                })
            except Exception:
                continue
    return dets, backpack_found


def downscale_for_browser(frame: np.ndarray) -> np.ndarray:
    if STREAM_MAX_WIDTH and frame.shape[1] > STREAM_MAX_WIDTH:
        scale = STREAM_MAX_WIDTH / frame.shape[1]
        new_h = int(frame.shape[0] * scale)
        return cv2.resize(frame, (STREAM_MAX_WIDTH, new_h), interpolation=cv2.INTER_AREA)
    return frame


# =========================
# BACKGROUND TASKS
# =========================
def _encode_frame_sync(frame: np.ndarray) -> Optional[bytes]:
    """Synchronous JPEG encoding - run in thread pool."""
    try:
        frame2 = downscale_for_browser(frame)
        ok, jpeg = cv2.imencode(
            ".jpg",
            frame2,
            [int(cv2.IMWRITE_JPEG_QUALITY), int(JPEG_QUALITY),
             int(cv2.IMWRITE_JPEG_OPTIMIZE), 1]
        )
        if ok:
            return jpeg.tobytes()
    except Exception as e:
        print(f"[ENCODER] Error encoding: {e}")
    return None


async def mjpeg_encoder_task():
    """Encode JPEG once at STREAM_FPS and share bytes across all clients."""
    global latest_jpeg_bytes, processing_frame

    interval = 1.0 / max(1, STREAM_FPS)
    print(f"[ENCODER] Starting MJPEG encoder at {STREAM_FPS} FPS")
    
    loop = asyncio.get_event_loop()
    encode_count = 0
    
    while True:
        t0 = time.time()
        
        try:
            if latest_frame is not None:
                processing_frame = True
                frame = latest_frame.copy()
                processing_frame = False
                
                # Run blocking encode in thread pool
                jpeg_bytes = await loop.run_in_executor(executor, _encode_frame_sync, frame)
                
                if jpeg_bytes:
                    async with latest_jpeg_lock:
                        latest_jpeg_bytes = jpeg_bytes
                    encode_count += 1
                    
                    if encode_count % 100 == 0:
                        print(f"[ENCODER] Encoded {encode_count} frames")
        except Exception as e:
            print(f"[ENCODER] Error: {e}")
            processing_frame = False

        dt = time.time() - t0
        await asyncio.sleep(max(0.001, interval - dt))


async def inference_task():
    """Run YOLO inference periodically on the latest frame."""
    global latest_result, inference_count, inference_start_time, last_inference_time_ms

    inference_start_time = time.time()
    last_infer_ts = 0.0
    last_processed_ts = 0.0

    while True:
        await asyncio.sleep(0.01)

        now = time.time()
        if now - last_infer_ts < MIN_INFERENCE_INTERVAL:
            continue
        last_infer_ts = now

        # Non-blocking frame read
        if latest_frame is None:
            continue
        frame = latest_frame.copy()
        ts = latest_frame_ts

        if ts == last_processed_ts:
            continue
        last_processed_ts = ts

        if model is None:
            continue

        t0 = time.time()
        try:
            # Run prediction with tracking enabled
            results = model.track(
                frame,
                device=device,
                verbose=False,
                half=USE_FP16,
                imgsz=INFERENCE_SIZE,
                conf=CONFIDENCE_THRESHOLD,
                persist=True,  # Keep track IDs across frames
                tracker="bytetrack.yaml",  # Use ByteTrack
            )
        except Exception:
            continue

        last_inference_time_ms = (time.time() - t0) * 1000.0
        inference_count += 1
        elapsed = time.time() - (inference_start_time or time.time())
        inf_fps = (inference_count / elapsed) if elapsed > 0 else 0.0

        dets, backpack_found = make_detections_from_results(results)
        
        # Update backpack detection status
        async with backpack_detection_lock:
            global backpack_detected
            backpack_detected = backpack_found
        
        payload = {
            "timestamp": ts,
            "num_detections": len(dets),
            "detections": dets,
            "inference_time_ms": round(last_inference_time_ms, 2),
            "inference_fps": round(inf_fps, 2),
            "total_inferences": inference_count,
            "backpack_detected": backpack_found,
        }
        save_detections_json(payload)
        async with latest_result_lock:
            latest_result = payload


# =========================
# LIFESPAN
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("\n" + "="*60)
    print("   WEBRTC WHIP INGEST + YOLO INFERENCE SERVER")
    print("="*60)
    
    global model, device
    torch.set_grad_enabled(False)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"[GPU] Detected: {torch.cuda.get_device_name(0)}")
    else:
        print("[WARNING] No GPU detected, using CPU")
    
    print(f"[MODEL] Loading {MODEL_PATH}...")
    model = YOLO(MODEL_PATH)
    print(f"[MODEL] ✓ Loaded successfully")

    print("[WORKER] Starting background tasks...")
    asyncio.create_task(mjpeg_encoder_task())
    asyncio.create_task(inference_task())
    
    print("\n" + "="*60)
    print("✓ SERVER READY!")
    print(f"✓ Open browser: http://localhost:{PORT}")
    print(f"✓ WHIP endpoint: http://localhost:{PORT}/whip")
    print(f"✓ Configure OBS → Settings → Stream:")
    print(f"   - Service: WHIP")
    print(f"   - Server: http://localhost:{PORT}/whip")
    print("="*60 + "\n")
    
    yield
    
    # Shutdown
    print("\n[SHUTDOWN] Closing peer connections...")
    for sid, pc in list(pcs.items()):
        try:
            await pc.close()
        except Exception:
            pass
        pcs.pop(sid, None)
    print("[SHUTDOWN] Complete")


# =========================
# APP
# =========================
app = FastAPI(title="WHIP WebRTC Ingest + YOLO + MJPEG", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# WEBRTC (WHIP) HELPERS
# =========================
def _parse_ice_sdpfrag(body: str) -> Tuple[Optional[str], List[str]]:
    """
    Very small parser for trickle-ICE SDP fragments:
    - mid from "a=mid:<mid>"
    - candidates from lines "a=candidate:..."
    """
    mid = None
    candidates = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("a=mid:"):
            mid = line.split(":", 1)[1].strip()
        if line.startswith("a=candidate:"):
            candidates.append(line[len("a="):])  # keep "candidate:..."
    return mid, candidates


async def _attach_video_track(pc: RTCPeerConnection):
    """
    When OBS sends a video track, consume frames and update latest_frame.
    """
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        state = pc.connectionState
        print(f"[WEBRTC] Connection state: {state}")
        if state in ["failed", "closed"]:
            print(f"[WEBRTC] ⚠ Connection {state} - stream will stop")
    
    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        state = pc.iceConnectionState
        print(f"[WEBRTC] ICE state: {state}")
        if state == "failed":
            print(f"[WEBRTC] ⚠ ICE failed - try restarting OBS stream")
    
    @pc.on("track")
    def on_track(track):
        print(f"[WEBRTC] Track received - Kind: {track.kind}, ID: {track.id}")
        
        if track.kind != "video":
            print(f"[WEBRTC] Skipping non-video track")
            return

        # Monitor track ended
        @track.on("ended")
        async def on_ended():
            print(f"[WEBRTC] ⚠ Track ended - stream stopped")

        async def recv_frames():
            global latest_frame, latest_frame_ts, capture_fps, _last_cap_count, _last_cap_t0, processing_frame
            frame_count = 0
            dropped_count = 0
            error_count = 0
            timeout_count = 0
            print(f"[WEBRTC] Starting frame receiver for video track...")
            
            while True:
                try:
                    # Use shorter timeout for faster response
                    av_frame = await asyncio.wait_for(track.recv(), timeout=0.5)
                    
                    # Success - reset counters
                    error_count = 0
                    if timeout_count > 0:
                        print(f"[WEBRTC] ✓ Recovered after {timeout_count} timeouts")
                        timeout_count = 0
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    # Don't stop - just keep trying! This is normal for aiortc
                    if timeout_count == 3:
                        print(f"[WEBRTC] ⚠ 3 consecutive timeouts (1.5s) - decoder may be stalled")
                        print(f"[WEBRTC]   If this persists, try: restart OBS stream or check OBS encoder settings")
                    elif timeout_count % 10 == 0:  # Log every 10 timeouts after that
                        print(f"[WEBRTC] ⚠ Still waiting... {timeout_count} timeouts ({timeout_count * 0.5:.1f}s)")
                    continue
                except Exception as e:
                    error_count += 1
                    if error_count % 10 == 1:
                        print(f"[WEBRTC] ⚠ Error #{error_count}: {type(e).__name__}: {str(e)[:100]}")
                    if error_count >= 50:
                        print(f"[WEBRTC] ✗ Stopping after {error_count} consecutive errors")
                        break
                    await asyncio.sleep(0.05)
                    continue

                frame_count += 1
                if frame_count == 1:
                    print(f"[WEBRTC] ✓ First frame! {av_frame.width}x{av_frame.height}")
                elif frame_count % 100 == 0:
                    print(f"[WEBRTC] ✓ {frame_count} frames (FPS: {capture_fps:.1f}, Dropped: {dropped_count})")

                # Skip processing if we're already processing a frame
                if processing_frame:
                    dropped_count += 1
                    continue
                
                # Convert immediately (blocking but quick)
                try:
                    img = av_frame.to_ndarray(format="bgr24")
                except Exception as e:
                    print(f"[WEBRTC] ⚠ Convert error: {e}")
                    continue
                
                ts = time.time()

                # capture fps metric
                _last_cap_count += 1
                dt = ts - _last_cap_t0
                if dt >= 1.0:
                    capture_fps = _last_cap_count / dt
                    _last_cap_count = 0
                    _last_cap_t0 = ts

                # Store frame (no lock needed - single writer)
                latest_frame = img
                latest_frame_ts = ts
            
            print(f"[WEBRTC] Receiver stopped. Total: {frame_count}, Dropped: {dropped_count}")

        asyncio.create_task(recv_frames())


# =========================
# ROUTES (WHIP)
# =========================
@app.post("/whip")
async def whip_ingest(request: Request):
    """
    WHIP: client (OBS) sends SDP offer in body (Content-Type: application/sdp)
    We return SDP answer with 201 + Location header.
    """
    print(f"[WHIP] Received connection request from {request.client.host}")
    
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/sdp":
        raise HTTPException(status_code=415, detail="Expected Content-Type: application/sdp")

    offer_sdp = (await request.body()).decode("utf-8", errors="ignore")
    print(f"[WHIP] Creating peer connection...")
    pc = RTCPeerConnection()

    await _attach_video_track(pc)

    offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
    await pc.setRemoteDescription(offer)

    # Create answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    sid = str(uuid.uuid4())
    pcs[sid] = pc
    
    print(f"[WHIP] ✓ Connection established (Session ID: {sid[:8]}...)")

    # WHIP expects:
    # - 201 Created
    # - Location: URL for the session resource
    # - Body: SDP answer (application/sdp)
    location = f"/whip/{sid}"

    return Response(
        content=pc.localDescription.sdp,
        status_code=201,
        media_type="application/sdp",
        headers={"Location": location},
    )


@app.patch("/whip/{sid}")
async def whip_trickle(sid: str, request: Request):
    """
    WHIP trickle ICE: OBS sends candidates via PATCH (application/trickle-ice-sdpfrag)
    We'll parse candidates and add them to the PeerConnection.
    """
    pc = pcs.get(sid)
    if pc is None:
        raise HTTPException(status_code=404, detail="Unknown session")

    ctype = request.headers.get("content-type", "").split(";")[0].strip()
    if ctype != "application/trickle-ice-sdpfrag":
        raise HTTPException(status_code=415, detail="Expected Content-Type: application/trickle-ice-sdpfrag")

    frag = (await request.body()).decode("utf-8", errors="ignore")
    mid, cand_lines = _parse_ice_sdpfrag(frag)

    # If we can't find a mid, aiortc still accepts candidates if sdpMid is None sometimes,
    # but we'll try to use the parsed mid when present.
    for cand_line in cand_lines:
        try:
            cand = candidate_from_sdp(cand_line)
            cand.sdpMid = mid
            cand.sdpMLineIndex = 0
            await pc.addIceCandidate(cand)
        except Exception:
            continue

    return Response(status_code=204)


@app.delete("/whip/{sid}")
async def whip_delete(sid: str):
    pc = pcs.pop(sid, None)
    if pc is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    await pc.close()
    return Response(status_code=204)


# =========================
# ROUTES (VIEW + API)
# =========================
HTML_PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>WebRTC Ingest Viewer (MJPEG)</title>
  <style>
    body { font-family: Arial, sans-serif; background:#1e1e1e; color:#fff; margin:0; padding:20px; }
    .container { max-width: 1400px; margin: 0 auto; }
    .video-container { position: relative; background:#000; border:2px solid #333; border-radius:8px; overflow:hidden; }
    #videoImg { width:100%; height:auto; display:block; }
    #canvas { position: absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; }
    .stats { margin-top:16px; background:#2d2d2d; padding:12px; border-radius:8px; }
    .row { display:flex; justify-content:space-between; margin:6px 0; }
    .label { color:#aaa; }
    .val { color:#0f0; font-weight:bold; }
    #anomalyAlert { display:none; position:fixed; top:20px; left:50%; transform:translateX(-50%); 
                    background:#ff0000; color:#fff; padding:20px 40px; border-radius:8px; 
                    font-size:24px; font-weight:bold; z-index:1000; box-shadow: 0 4px 20px rgba(255,0,0,0.5); 
                    animation: pulse 1s infinite; }
    @keyframes pulse { 0%, 100% { opacity:1; } 50% { opacity:0.7; } }
  </style>
</head>
<body>
<div id="anomalyAlert">⚠️ ANOMALY DETECTED: PERSON ⚠️</div>
<div class="container">
  <h1>🎥 WebRTC Ingest (WHIP) → MJPEG</h1>
  <div class="video-container">
    <img id="videoImg" src="/stream" />
    <canvas id="canvas"></canvas>
  </div>
  <div class="stats">
    <div class="row"><span class="label">Capture FPS</span><span class="val" id="cap">-</span></div>
    <div class="row"><span class="label">Inference FPS</span><span class="val" id="inf">-</span></div>
    <div class="row"><span class="label">Inference ms</span><span class="val" id="ms">-</span></div>
    <div class="row"><span class="label">Detections</span><span class="val" id="det">-</span></div>
  </div>
</div>
<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const img = document.getElementById('videoImg');

// Resize canvas to match image
function resizeCanvas() {
  canvas.width = img.clientWidth;
  canvas.height = img.clientHeight;
}
img.addEventListener('load', resizeCanvas);
window.addEventListener('resize', resizeCanvas);

let detections = [];
let frameWidth = 1;
let frameHeight = 1;

// Fetch detections and stats
async function poll(){
  try{
    const r = await fetch("/stats");
    const s = await r.json();
    document.getElementById("cap").textContent = (s.capture_fps ?? 0).toFixed(1);
    document.getElementById("inf").textContent = (s.inference_fps ?? 0).toFixed(1);
    document.getElementById("ms").textContent  = (s.last_inference_time_ms ?? 0).toFixed(1);
    document.getElementById("det").textContent = (s.num_detections ?? 0);
  }catch(e){}
  
  try{
    const dr = await fetch("/detections");
    const d = await dr.json();
    if (d.detections) {
      detections = d.detections;
      frameWidth = d.frame_width || 1;
      frameHeight = d.frame_height || 1;
      
      // Show/hide anomaly alert based on backpack detection
      const alert = document.getElementById('anomalyAlert');
      if (d.backpack_detected) {
        alert.style.display = 'block';
      } else {
        alert.style.display = 'none';
      }
    }
  }catch(e){}
  
  setTimeout(poll, 200);
}
poll();

// Draw bounding boxes
function drawBoxes() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  if (!detections.length || !img.clientWidth) {
    requestAnimationFrame(drawBoxes);
    return;
  }
  
  // Scale factor from original frame to displayed image
  const scaleX = canvas.width / frameWidth;
  const scaleY = canvas.height / frameHeight;
  
  ctx.lineWidth = 2;
  ctx.font = '14px Arial';
  
  for (const det of detections) {
    const [x1, y1, x2, y2] = det.bbox;
    const sx1 = x1 * scaleX;
    const sy1 = y1 * scaleY;
    const sx2 = x2 * scaleX;
    const sy2 = y2 * scaleY;
    
    // Use red color for backpacks (anomaly), blue for others
    const isBackpack = det.is_backpack || false;
    const color = isBackpack ? '#ff0000' : '#0000ff';
    
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    
    // Draw box
    ctx.strokeRect(sx1, sy1, sx2 - sx1, sy2 - sy1);
    
    // Draw label background
    const trackInfo = det.track_id ? ` ID:${det.track_id}` : '';
    const label = `${det.class_name} ${(det.confidence * 100).toFixed(0)}%${trackInfo}`;
    const metrics = ctx.measureText(label);
    const textHeight = 16;
    const textY = Math.max(textHeight, sy1 - 4);
    
    ctx.fillStyle = color;
    ctx.fillRect(sx1, textY - textHeight, metrics.width + 8, textHeight + 4);
    
    // Draw label text
    ctx.fillStyle = '#fff';
    ctx.fillText(label, sx1 + 4, textY - 2);
  }
  
  requestAnimationFrame(drawBoxes);
}

drawBoxes();
</script>
</body>
</html>
"""

@app.get("/")
def index():
    return HTMLResponse(HTML_PAGE)

def generate_mjpeg_stream():
    boundary = b"--frame\r\n"
    while True:
        # NOTE: generator is sync; we "busy-wait" lightly.
        # It reads latest_jpeg_bytes updated by async task.
        jpeg_bytes = None
        # We cannot await here, so we use the last known bytes without locking.
        # If you want strict safety, switch to an async generator.
        global latest_jpeg_bytes
        jpeg_bytes = latest_jpeg_bytes

        if not jpeg_bytes:
            time.sleep(0.05)
            continue

        yield (
            boundary +
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: " + str(len(jpeg_bytes)).encode() + b"\r\n\r\n" +
            jpeg_bytes + b"\r\n"
        )
        time.sleep(0.001)

@app.get("/stream")
def stream():
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers=headers,
    )

@app.get("/detections")
async def detections():
    async with latest_result_lock:
        if latest_result is None:
            return JSONResponse({"status": "no_detections", "detections": [], "frame_width": 1, "frame_height": 1, "backpack_detected": False})
        
        # Include frame dimensions for client-side scaling (no lock needed)
        w = latest_frame.shape[1] if latest_frame is not None else 1
        h = latest_frame.shape[0] if latest_frame is not None else 1
        
        return JSONResponse({
            **latest_result,
            "frame_width": w,
            "frame_height": h
        })

@app.get("/stats")
async def stats():
    async with latest_result_lock:
        dets = 0 if latest_result is None else int(latest_result.get("num_detections", 0))
        inf_fps = 0.0 if latest_result is None else float(latest_result.get("inference_fps", 0.0))

    return JSONResponse({
        "capture_fps": float(capture_fps),
        "inference_fps": float(inf_fps),
        "last_inference_time_ms": float(last_inference_time_ms),
        "num_detections": dets,
        "stream_fps": int(STREAM_FPS),
        "stream_max_width": int(STREAM_MAX_WIDTH),
        "jpeg_quality": int(JPEG_QUALITY),
        "active_sessions": len(pcs),
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
