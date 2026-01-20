import uuid
import asyncio
import time
from typing import Optional, Dict, Any, List
import numpy as np
import cv2
import torch
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay
from aiortc.sdp import candidate_from_sdp
from ultralytics import YOLO
import uvicorn

# Config
HOST = "0.0.0.0"
PORT = 8000

MODEL_PATH = "yolo11s.pt"      # YOLOv11 Small
CONFIDENCE = 0.35
IMG_SIZE = 480                # Smaller = faster inference
USE_FP16 = True                # Enable half precision for 2x GPU speedup

# Anomaly detection - classes that trigger warnings
ANOMALY_CLASSES = ["bear", "cow"]

# Global State
app = FastAPI()

# Allowed Access Points
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebRTC state
pcs = {}
relay = MediaRelay()
ingest_video_track = None

# YOLO model
model: Optional[YOLO] = None
device: str = "cpu"

# Current detection state
current_detections: List[Dict[str, Any]] = []
detections_lock = asyncio.Lock()

# Performance metrics
inference_count: int = 0
inference_start_time: Optional[float] = None
last_inference_time: float = 0.0
inference_fps: float = 0.0
is_inferencing: bool = False  # Flag to prevent concurrent inference

# Annotated frame state
latest_raw_frame: Optional[np.ndarray] = None
latest_annotated_jpeg: Optional[bytes] = None
annotated_frame_lock = asyncio.Lock()
frame_dimensions: tuple[int, int] = (0, 0)  # (width, height)

# YOLO Interference
def _run_yolo_on_frame(frame_bgr: np.ndarray) -> tuple[List[Dict[str, Any]], float]:
    """Runs YOLO inference. Returns (detections, inference_ms)."""
    t0 = time.time()
    results = model(
        frame_bgr, 
        imgsz=IMG_SIZE, 
        conf=CONFIDENCE, 
        device=device, 
        verbose=False,
        half=USE_FP16,
        agnostic_nms=True
    )
    ms = (time.time() - t0) * 1000.0

    dets: List[Dict[str, Any]] = []
    for r in results:
        names = getattr(r, "names", {})
        for b in r.boxes:
            cls = int(b.cls[0])
            conf = float(b.conf[0])
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            class_name = names.get(cls, str(cls))
            dets.append({
                "class_id": cls,
                "class_name": class_name,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
                "is_anomaly": class_name.lower() in [ac.lower() for ac in ANOMALY_CLASSES]
            })
    return dets, ms

# Interference Worker
async def inference_worker():
    """
    Continuously pull frames from WebRTC and run inference.
    Drops all buffered frames - only processes the latest frame.
    """
    global inference_count, inference_start_time, last_inference_time, inference_fps
    global current_detections, is_inferencing
    
    print("[INFERENCE] Worker started - waiting for video stream...")
    
    while True:
        await asyncio.sleep(0.001)  # Small sleep to prevent busy-wait
        
        # Wait for stream
        if ingest_video_track is None:
            await asyncio.sleep(0.1)
            continue
        
        # Skip if already processing (prevents concurrent inference)
        if is_inferencing:
            continue
        
        is_inferencing = True
        
        try:
            # Drain buffer to get ONLY the latest frame (drop all buffered frames)
            latest_frame = None
            frames_drained = 0
            
            # Keep reading frames until we hit timeout (no more frames in buffer)
            while True:
                try:
                    frame = await asyncio.wait_for(ingest_video_track.recv(), timeout=0.001)
                    latest_frame = frame
                    frames_drained += 1
                except asyncio.TimeoutError:
                    break  # No more frames in buffer
            
            if latest_frame is None:
                # No frames available, try again
                is_inferencing = False
                continue
            
            if frames_drained > 1:
                print(f"[BUFFER] Drained {frames_drained} frames, processing latest only")
            
            # Decode only the latest frame
            img = latest_frame.to_ndarray(format="bgr24")
            
            # Run inference
            dets, infer_ms = await asyncio.to_thread(_run_yolo_on_frame, img)
            
            # Update metrics
            inference_count += 1
            current_time = time.time()
            
            if inference_start_time is None:
                inference_start_time = current_time
            
            elapsed = current_time - inference_start_time
            inference_fps = inference_count / elapsed if elapsed > 0 else 0.0
            last_inference_time = current_time
            
            # Store detections and raw frame for annotation
            async with detections_lock:
                current_detections = dets
            
            global latest_raw_frame
            async with annotated_frame_lock:
                latest_raw_frame = img.copy()
                frame_dimensions = (img.shape[1], img.shape[0])
            
            # Log results
            anomalies = [d for d in dets if d.get('is_anomaly', False)]
            if dets:
                print(f"\n[INFERENCE #{inference_count}] @ {inference_fps:.1f} FPS - Found {len(dets)} object(s) ({infer_ms:.1f}ms):")
                for i, d in enumerate(dets, 1):
                    anomaly_marker = "!" if d.get('is_anomaly', False) else ""
                    print(f"  {i}. {d['class_name']} ({d['confidence']*100:.1f}%){anomaly_marker}")
            else:
                print(f"[INFERENCE #{inference_count}] @ {inference_fps:.1f} FPS - No objects detected ({infer_ms:.1f}ms)")
            
            if anomalies:
                print(f"ANOMALY: {', '.join([a['class_name'] for a in anomalies])}")
        
        except asyncio.TimeoutError:
            print("[INFERENCE] ! Timeout waiting for frame")
        except Exception as e:
            print(f"[INFERENCE] ! Error: {type(e).__name__}: {str(e)[:100]}")
        finally:
            is_inferencing = False

# Annotation Worker - Draws bounding boxes
async def annotation_worker():
    """Background worker that draws bounding boxes on frames."""
    global latest_annotated_jpeg
    
    print("[ANNOTATION] Worker started - waiting for frames...")
    
    while True:
        await asyncio.sleep(0.05)  # Annotate at ~20 FPS
        
        # Get current frame and detections
        async with annotated_frame_lock:
            frame = latest_raw_frame
        
        async with detections_lock:
            dets = current_detections.copy()
        
        if frame is None:
            continue
        
        try:
            # Draw on a copy (even if no detections, we still serve the frame)
            annotated = frame.copy()
            
            # Draw each detection
            for det in dets:
                x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
                is_anomaly = det.get("is_anomaly", False)
                
                # Color: red for anomalies, green for normal
                color = (0, 0, 255) if is_anomaly else (0, 255, 0)
                thickness = 3 if is_anomaly else 2
                
                # Draw bounding box
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
                
                # Draw label background
                label = f"{det['class_name']} {det['confidence']*100:.1f}%"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                font_thickness = 2
                (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
                
                # Draw filled rectangle for text background
                cv2.rectangle(annotated, (x1, y1 - label_h - 10), (x1 + label_w, y1), color, -1)
                
                # Draw text
                cv2.putText(annotated, label, (x1, y1 - 5), font, font_scale, (255, 255, 255), font_thickness)
            
            # Always encode to JPEG (even if no detections)
            ret, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                async with annotated_frame_lock:
                    latest_annotated_jpeg = buffer.tobytes()
                # Log first successful annotation
                if inference_count == 1 and len(dets) == 0:
                    print("[ANNOTATION] ✓ First frame encoded (no detections yet)")
                elif inference_count == 1:
                    print(f"[ANNOTATION] ✓ First frame encoded with {len(dets)} detection(s)")
            else:
                print("[ANNOTATION] ⚠ Failed to encode JPEG")
        
        except Exception as e:
            print(f"[ANNOTATION] ⚠ Error: {type(e).__name__}: {str(e)}")
        except Exception as e:
            print(f"[ANNOTATION] ⚠ Error: {type(e).__name__}: {str(e)[:100]}")

# API Endpoints
@app.get("/detections")
async def get_detections():
    """Get current detections."""
    async with detections_lock:
        anomalies = [d for d in current_detections if d.get('is_anomaly', False)]
        return {
            "timestamp": last_inference_time,
            "num_detections": len(current_detections),
            "detections": current_detections,
            "inference_count": inference_count,
            "inference_fps": round(inference_fps, 2),
            "has_anomaly": len(anomalies) > 0,
            "anomaly_count": len(anomalies)
        }

@app.get("/stats")
async def get_stats():
    """Get performance statistics."""
    return {
        "inference_count": inference_count,
        "inference_fps": round(inference_fps, 2),
        "has_stream": ingest_video_track is not None,
        "is_processing": is_inferencing
    }

@app.get("/annotated-frame.jpg")
async def get_annotated_frame():
    """Get the latest frame with bounding boxes drawn."""
    async with annotated_frame_lock:
        if latest_annotated_jpeg is None:
            raise HTTPException(status_code=404, detail="No annotated frame available yet")
        jpeg = latest_annotated_jpeg
    
    return Response(content=jpeg, media_type="image/jpeg")

@app.get("/video-view")
async def video_view():
    """HTML page for viewing annotated video stream."""
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Live Detection Video - Hybrid Server</title>
    <style>
      body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: #fff;
        margin: 0;
        padding: 20px;
        min-height: 100vh;
      }}
      .container {{
        max-width: 1400px;
        margin: 0 auto;
      }}
      h1 {{
        text-align: center;
        margin-bottom: 10px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
      }}
      .video-container {{
        background: rgba(0,0,0,0.3);
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        text-align: center;
      }}
      #videoFrame {{
        max-width: 100%;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
      }}
      .stats {{
        background: rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 15px;
        margin: 20px 0;
        backdrop-filter: blur(10px);
        display: flex;
        justify-content: space-around;
        flex-wrap: wrap;
        gap: 15px;
      }}
      .stat-box {{
        background: rgba(255,255,255,0.15);
        border-radius: 8px;
        padding: 12px 20px;
        min-width: 120px;
        text-align: center;
      }}
      .stat-label {{
        font-size: 13px;
        opacity: 0.8;
        margin-bottom: 5px;
      }}
      .stat-value {{
        font-size: 24px;
        font-weight: bold;
        color: #ffd700;
      }}
      .anomaly-warning {{
        background: #ff0000;
        color: #fff;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        font-size: 18px;
        margin: 15px 0;
        animation: pulse 1s infinite;
        display: none;
      }}
      @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.7; }}
      }}
      .info {{
        text-align: center;
        opacity: 0.7;
        font-size: 14px;
        margin: 10px 0;
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Live Detection Video Stream</h1>
      <p class="info">Real-time YOLO Object Detection with Bounding Boxes</p>
      
      <div id="anomalyWarning" class="anomaly-warning"></div>
      
      <div class="stats">
        <div class="stat-box">
          <div class="stat-label">Inferences</div>
          <div class="stat-value" id="inferenceCount">0</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">FPS</div>
          <div class="stat-value" id="inferenceFps">0.0</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Objects</div>
          <div class="stat-value" id="objectCount">0</div>
        </div>
      </div>
      
      <div class="video-container">
        <img id="videoFrame" src="/annotated-frame.jpg" alt="Waiting for stream..." onload="scheduleNextFrame()">
      </div>
      
      <p class="info">Green boxes: Normal objects | Red boxes: Anomalies ({{', '.join(ANOMALY_CLASSES)}})</p>
    </div>
    
    <script>
      const img = document.getElementById('videoFrame');
      let frameNumber = 0;
      
      // Refresh video frame using onload callback for smoother updates
      function scheduleNextFrame() {{
        frameNumber++;
        // Small delay, then load next frame
        setTimeout(() => {{
          img.src = `/annotated-frame.jpg?frame=${{frameNumber}}`;
        }}, 16);  // ~60 FPS max
      }}
      
      // Initial load
      scheduleNextFrame();
      // Initial load
      scheduleNextFrame();
      
      // Update stats
      async function updateStats() {{
        try {{
          const response = await fetch('/detections');
          const data = await response.json();
          
          document.getElementById('inferenceCount').textContent = data.inference_count || 0;
          document.getElementById('inferenceFps').textContent = (data.inference_fps || 0).toFixed(1);
          document.getElementById('objectCount').textContent = data.num_detections || 0;
          
          // Show anomaly warning
          const warning = document.getElementById('anomalyWarning');
          if (data.has_anomaly && data.detections) {{
            const anomalies = data.detections.filter(d => d.is_anomaly);
            const anomalyNames = anomalies.map(a => a.class_name.toUpperCase()).join(', ');
            warning.textContent = `ANOMALY DETECTED: ${{anomalyNames}}`;
            warning.style.display = 'block';
          }} else {{
            warning.style.display = 'none';
          }}
        }} catch (error) {{
          console.error('Error fetching stats:', error);
        }}
      }}
      
      // Update stats every 200ms
      setInterval(updateStats, 200);
      updateStats();
    </script>
  </body>
</html>
    """)

# WEBRTC Endpoints (WHIP Protocol)
@app.post("/whip")
async def whip(request: Request):
    """Accept WebRTC offer from OBS via WHIP protocol."""
    global ingest_video_track

    pc = RTCPeerConnection()
    sid = str(uuid.uuid4())
    pcs[sid] = pc

    @pc.on("track")
    def on_track(track):
        global ingest_video_track
        print(f"[WHIP] Track received: {track.kind}")
        if track.kind == "video":
            ingest_video_track = relay.subscribe(track)
            print("[WHIP] ✓ Video track connected - inference will begin")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"[WHIP] Connection state: {pc.connectionState}")
        if pc.connectionState == "failed" or pc.connectionState == "closed":
            await pc.close()
            if sid in pcs:
                del pcs[sid]

    # WHIP protocol: body is raw SDP, not JSON
    offer = RTCSessionDescription(
        sdp=(await request.body()).decode(),
        type="offer"
    )

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # WHIP protocol: return SDP as text, not JSON
    return Response(
        pc.localDescription.sdp,
        status_code=201,
        media_type="application/sdp",
        headers={"Location": f"/whip/{sid}"}
    )

@app.patch("/whip/{sid}")
async def whip_trickle(sid: str, request: Request):
    """Handle ICE trickle candidates via WHIP."""
    pc = pcs.get(sid)
    if not pc:
        raise HTTPException(status_code=404)

    frag = (await request.body()).decode()
    for line in frag.splitlines():
        if line.startswith("a=candidate:"):
            cand = candidate_from_sdp(line[2:])
            await pc.addIceCandidate(cand)

    return Response(status_code=204)

# HTML Viewer
@app.get("/")
def index():
    """Serve the viewer page."""
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Pure Inference Server - YOLO Detection Viewer</title>
    <style>
      body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: #fff;
        margin: 0;
        padding: 20px;
        min-height: 100vh;
      }}
      .container {{
        max-width: 1200px;
        margin: 0 auto;
      }}
      h1 {{
        text-align: center;
        margin-bottom: 10px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
      }}
      .stats {{
        background: rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        backdrop-filter: blur(10px);
      }}
      .stat-row {{
        display: flex;
        justify-content: space-around;
        flex-wrap: wrap;
        gap: 15px;
      }}
      .stat-box {{
        background: rgba(255,255,255,0.15);
        border-radius: 8px;
        padding: 15px 25px;
        min-width: 150px;
        text-align: center;
      }}
      .stat-label {{
        font-size: 14px;
        opacity: 0.8;
        margin-bottom: 5px;
      }}
      .stat-value {{
        font-size: 32px;
        font-weight: bold;
        color: #ffd700;
      }}
      .detections-container {{
        background: rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        backdrop-filter: blur(10px);
        min-height: 200px;
      }}
      .detection-item {{
        background: rgba(255,255,255,0.15);
        border-left: 4px solid #00ff00;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 10px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: transform 0.2s;
      }}
      .detection-item:hover {{
        transform: translateX(5px);
      }}
      .detection-item.anomaly {{
        border-left-color: #ff0000;
        background: rgba(255,0,0,0.2);
        animation: pulse 1.5s infinite;
      }}
      @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.7; }}
      }}
      .detection-name {{
        font-weight: bold;
        font-size: 18px;
      }}
      .detection-confidence {{
        opacity: 0.8;
        font-size: 16px;
      }}
      .anomaly-warning {{
        background: #ff0000;
        color: #fff;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        margin: 15px 0;
        animation: pulse 1s infinite;
      }}
      .no-detections {{
        text-align: center;
        opacity: 0.6;
        padding: 40px;
        font-size: 18px;
      }}
      .stream-status {{
        text-align: center;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
      }}
      .stream-active {{
        background: rgba(0,255,0,0.2);
        border: 2px solid #00ff00;
      }}
      .stream-inactive {{
        background: rgba(255,0,0,0.2);
        border: 2px solid #ff0000;
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <h1>🎯 Pure Inference Server</h1>
      <p style="text-align: center; opacity: 0.8;">Real-time YOLO Detection • Port {PORT}</p>
      
      <div class="stream-status" id="streamStatus">
        <span id="streamText">Waiting for stream...</span>
      </div>
      
      <div class="stats">
        <div class="stat-row">
          <div class="stat-box">
            <div class="stat-label">Inferences</div>
            <div class="stat-value" id="inferenceCount">0</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">FPS</div>
            <div class="stat-value" id="inferenceFps">0.0</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Objects Detected</div>
            <div class="stat-value" id="objectCount">0</div>
          </div>
        </div>
      </div>
      
      <div id="anomalyWarningContainer"></div>
      
      <div class="detections-container">
        <h2 style="margin-top: 0;">Detected Objects</h2>
        <div id="detectionsList">
          <div class="no-detections">No objects detected yet</div>
        </div>
      </div>
    </div>
    
    <script>
      let lastDetectionCount = 0;
      
      async function updateDetections() {{
        try {{
          const response = await fetch('/detections');
          const data = await response.json();
          
          // Update stats
          document.getElementById('inferenceCount').textContent = data.inference_count || 0;
          document.getElementById('inferenceFps').textContent = (data.inference_fps || 0).toFixed(1);
          document.getElementById('objectCount').textContent = data.num_detections || 0;
          
          // Update stream status
          const streamStatus = document.getElementById('streamStatus');
          const streamText = document.getElementById('streamText');
          if (data.inference_count > 0) {{
            streamStatus.className = 'stream-status stream-active';
            streamText.textContent = '✓ Stream Active - Processing';
          }} else {{
            streamStatus.className = 'stream-status stream-inactive';
            streamText.textContent = 'Waiting for stream...';
          }}
          
          // Update anomaly warning
          const anomalyContainer = document.getElementById('anomalyWarningContainer');
          if (data.has_anomaly) {{
            const anomalies = data.detections.filter(d => d.is_anomaly);
            const anomalyNames = anomalies.map(a => a.class_name.toUpperCase()).join(', ');
            anomalyContainer.innerHTML = `
              <div class="anomaly-warning">
                ANOMALY DETECTED: ${{anomalyNames}}
              </div>
            `;
          }} else {{
            anomalyContainer.innerHTML = '';
          }}
          
          // Update detections list
          const detectionsList = document.getElementById('detectionsList');
          if (data.detections && data.detections.length > 0) {{
            const uniqueObjects = {{}};
            data.detections.forEach(det => {{
              const key = det.class_name;
              if (!uniqueObjects[key]) {{
                uniqueObjects[key] = {{
                  ...det,
                  count: 1
                }};
              }} else {{
                uniqueObjects[key].count++;
                uniqueObjects[key].confidence = Math.max(uniqueObjects[key].confidence, det.confidence);
              }}
            }});
            
            detectionsList.innerHTML = Object.values(uniqueObjects)
              .sort((a, b) => b.confidence - a.confidence)
              .map(det => {{
                const anomalyClass = det.is_anomaly ? ' anomaly' : '';
                const anomalyIcon = det.is_anomaly ? '!' : '';
                const countText = det.count > 1 ? ` (×${{det.count}})` : '';
                return `
                  <div class="detection-item${{anomalyClass}}">
                    <span class="detection-name">${{det.class_name.toUpperCase()}}${{countText}}${{anomalyIcon}}</span>
                    <span class="detection-confidence">${{(det.confidence * 100).toFixed(1)}}%</span>
                  </div>
                `;
              }}).join('');
          }} else {{
            detectionsList.innerHTML = '<div class="no-detections">No objects detected</div>';
          }}
          
        }} catch (error) {{
          console.error('Error fetching detections:', error);
        }}
      }}
      
      // Update every 100ms for responsive UI
      setInterval(updateDetections, 100);
      updateDetections();
    </script>
  </body>
</html>
    """)

# Server Startup / Shutdown Process
@app.on_event("startup")
async def startup():
    global model, device
    
    print("[STARTUP] Pure Inference Server starting...")
    
    # Setup GPU
    if torch.cuda.is_available():
        device = "cuda"
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.enabled = True
        print(f"[GPU] Detected: {{torch.cuda.get_device_name(0)}}")
        print(f"[GPU] Memory: {{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}} GB")
    else:
        device = "cpu"
        print("[WARNING] CUDA not available, using CPU")
    
    torch.set_grad_enabled(False)
    
    # Load YOLO model
    print(f"[MODEL] Loading {{MODEL_PATH}}...")
    model = await asyncio.to_thread(YOLO, MODEL_PATH)
    await asyncio.to_thread(model.to, device)
    
    # GPU warmup
    if device == "cuda":
        print("[MODEL] Warming up GPU...")
        dummy_frame = np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
        for _ in range(3):
            _ = model(dummy_frame, imgsz=IMG_SIZE, device=device, verbose=False, half=USE_FP16)
        torch.cuda.synchronize()
    
    print(f"✓ Model loaded on {{device.upper()}} with FP16={{USE_FP16}}")
    
    # Start workers
    asyncio.create_task(inference_worker())
    asyncio.create_task(annotation_worker())
    
    print(f"✓ Server ready: http://localhost:{{PORT}}")
    print(f"✓ Detection Stats: http://localhost:{{PORT}}/")
    print(f"✓ Live Video View: http://localhost:{{PORT}}/video-view")
    print(f"✓ WHIP endpoint: http://localhost:{{PORT}}/whip")
    print(f"✓ Ready to receive WebRTC stream from OBS")

@app.on_event("shutdown")
async def shutdown():
    print("[SHUTDOWN] Closing all peer connections...")
    for pc in pcs.values():
        await pc.close()
    pcs.clear()

# Run
if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
