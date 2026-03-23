import asyncio
from typing import Optional
import numpy as np
import cv2
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import aiortc
import aiortc.contrib.media
import aiortc.sdp
import uvicorn

# Config
HOST = "0.0.0.0"
PORT = 8000

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
pc: Optional[aiortc.RTCPeerConnection] = None
relay = aiortc.contrib.media.MediaRelay()
ingest_video_track = None

# Frame state
latest_frame: Optional[np.ndarray] = None
latest_jpeg: Optional[bytes] = None
frame_lock = asyncio.Lock()
frame_count: int = 0

# Frame processing worker
async def frame_worker():
    """
    Continuously pull frames from WebRTC, decode them, and re-encode as JPEG.
    """
    global frame_count, latest_frame, latest_jpeg
    
    print("[FRAME WORKER] Started - waiting for video stream...")
    
    while True:
        # Wait for stream
        if ingest_video_track is None:
            await asyncio.sleep(0.1)
            continue
        
        try:
            # Receive a frame (this will block until a frame is available)
            frame = await ingest_video_track.recv()
            
            # Now drain any buffered frames to get the latest
            frames_drained = 1
            latest_frame_obj = frame
            
            while True:
                try:
                    frame = await asyncio.wait_for(ingest_video_track.recv(), timeout=0.001)
                    latest_frame_obj = frame
                    frames_drained += 1
                except asyncio.TimeoutError:
                    break
            
            if frames_drained > 1:
                print(f"[BUFFER] Drained {frames_drained} frames, using latest")
            
            # Convert to numpy array (BGR format)
            img = latest_frame_obj.to_ndarray(format="bgr24")
            
            # Encode to JPEG
            ret, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            if ret:
                async with frame_lock:
                    latest_frame = img.copy()
                    latest_jpeg = buffer.tobytes()
                    frame_count += 1
                
                if frame_count == 1:
                    print(f"[FRAME WORKER] First frame received and processed!")
                elif frame_count % 100 == 0:
                    print(f"[FRAME WORKER] Processed {frame_count} frames")
            else:
                print("[FRAME WORKER] Failed to encode JPEG")
        
        except Exception as e:
            print(f"[FRAME WORKER] Error: {type(e).__name__}: {str(e)}")

# Server Startup / Shutdown Process
@app.on_event("startup")
async def startup():
    print("[STARTUP] Simple Passthrough Server starting...")
    
    asyncio.create_task(frame_worker())
    
    print(f"Server ready: http://localhost:{PORT}")
    print(f"Live Video View: http://localhost:{PORT}/video-view")
    print(f"WHIP endpoint: http://localhost:{PORT}/whip")
    print(f"Ready to receive WebRTC stream from OBS")

@app.on_event("shutdown")
async def shutdown():
    global pc
    print("[SHUTDOWN] Closing peer connection...")
    if pc:
        await pc.close()

# Endpoint for OBS to stream to
# Establish connection via WHIP (WebRTC-HTTP Ingestion Protocol)
@app.post("/whip")
async def whip(request: Request):
    global ingest_video_track, pc

    # Close existing connection if any
    if pc is not None:
        print("[WHIP] Closing existing peer connection...")
        await pc.close()
        ingest_video_track = None

    pc = aiortc.RTCPeerConnection()
    print("[WHIP] New peer connection created")

    # Receive the video track from OBS
    @pc.on("track")
    def on_track(track):
        global ingest_video_track
        print(f"[WHIP] Track received: {track.kind}")
        if track.kind == "video":
            ingest_video_track = relay.subscribe(track)
            print("[WHIP] Video track connected - frame processing will begin")
        else:
            print(f"[WHIP] Ignoring non-video track: {track.kind}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"[WHIP] Connection state: {pc.connectionState}")
        if pc.connectionState == "failed" or pc.connectionState == "closed":
            print("[WHIP] Connection closed or failed")
            await pc.close()

    # WEBRTC Handshake via WHIP
    offer = aiortc.RTCSessionDescription(sdp=(await request.body()).decode(),type="offer")

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return Response(pc.localDescription.sdp,status_code=201,media_type="application/sdp",headers={"Location": "/whip/obs"}
    )

@app.patch("/whip/obs")
async def whip_trickle(request: Request):
    if not pc:
        raise HTTPException(status_code=404)

    sdpfragement = (await request.body()).decode()
    for line in sdpfragement.splitlines():
        if line.startswith("a=candidate:"):
            cand = aiortc.sdp.candidate_from_sdp(line[2:])
            await pc.addIceCandidate(cand)

    return Response(status_code=204)

# Endpoint for frame stats
@app.get("/stats")
async def get_stats():
    return {
        "frame_count": frame_count,
        "has_stream": ingest_video_track is not None,
    }

@app.get("/frame.jpg")
async def get_frame():
    async with frame_lock:
        if latest_jpeg is None:
            raise HTTPException(status_code=404, detail="No frame available yet")
        jpeg_data = latest_jpeg
    
    return Response(content=jpeg_data, media_type="image/jpeg")

@app.get("/video-view")
async def video_view():
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Live Video Stream - Simple Passthrough</title>
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
      <h1>Live Video Stream</h1>
      <p class="info">Simple WebRTC Passthrough Server</p>
      
      <div class="stats">
        <div class="stat-box">
          <div class="stat-label">Frames Processed</div>
          <div class="stat-value" id="frameCount">0</div>
        </div>
      </div>
      
      <div class="video-container">
        <img id="videoFrame" src="/frame.jpg" alt="Waiting for stream..." onload="scheduleNextFrame()">
      </div>
      
      <p class="info">Raw video feed with no processing</p>
    </div>
    
    <script>
      const img = document.getElementById('videoFrame');
      let frameNumber = 0;
      
      // Refresh video frame using onload callback for smoother updates
      function scheduleNextFrame() {{
        frameNumber++;
        // Small delay, then load next frame
        setTimeout(() => {{
          img.src = `/frame.jpg?frame=${{frameNumber}}`;
        }}, 16);  // ~60 FPS max
      }}
      
      // Initial load
      scheduleNextFrame();
      
      // Update stats
      async function updateStats() {{
        try {{
          const response = await fetch('/stats');
          const data = await response.json();
          
          document.getElementById('frameCount').textContent = data.frame_count || 0;
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

# HTML Viewer
@app.get("/")
def index():
    """Serve the viewer page."""
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Simple Passthrough Server</title>
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
      .link {{
        display: block;
        text-align: center;
        padding: 15px;
        background: rgba(255,255,255,0.15);
        border-radius: 8px;
        margin: 15px 0;
        text-decoration: none;
        color: #ffd700;
        font-weight: bold;
        transition: transform 0.2s;
      }}
      .link:hover {{
        transform: translateY(-2px);
        background: rgba(255,255,255,0.25);
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <h1>📹 Simple Passthrough Server</h1>
      <p style="text-align: center; opacity: 0.8;">WebRTC Video Stream • Port {PORT}</p>
      
      <div class="stream-status" id="streamStatus">
        <span id="streamText">Waiting for stream...</span>
      </div>
      
      <div class="stats">
        <div class="stat-row">
          <div class="stat-box">
            <div class="stat-label">Frames Processed</div>
            <div class="stat-value" id="frameCount">0</div>
          </div>
        </div>
      </div>
      
      <a href="/video-view" class="link">View Live Video Stream →</a>
    </div>
    
    <script>
      async function updateStats() {{
        try {{
          const response = await fetch('/stats');
          const data = await response.json();
          
          // Update stats
          document.getElementById('frameCount').textContent = data.frame_count || 0;
          
          // Update stream status
          const streamStatus = document.getElementById('streamStatus');
          const streamText = document.getElementById('streamText');
          if (data.has_stream) {{
            streamStatus.className = 'stream-status stream-active';
            streamText.textContent = '✓ Stream Active - Processing';
          }} else {{
            streamStatus.className = 'stream-status stream-inactive';
            streamText.textContent = 'Waiting for stream...';
          }}
        }} catch (error) {{
          console.error('Error fetching stats:', error);
        }}
      }}
      
      // Update every 200ms for responsive UI
      setInterval(updateStats, 200);
      updateStats();
    </script>
  </body>
</html>
    """)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
