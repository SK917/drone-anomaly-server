# VALM stands for Vigilant Aerial Live Monitor (Based on the first letter of our first names)

import asyncio
import logging
import torch
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import uvicorn

import server_engine.state as state
from server_engine.inference import inference_worker
from server_engine.annotation import annotation_worker
from server_engine.websocket_manager import manager, router as ws_router
from server_engine.whip import router as whip_router
from server_engine.inference import router as inference_router
from server_engine.annotation import router as annotation_router

HOST = "0.0.0.0"
PORT = 8000

# Server Startup / Shutdown Process
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("Initializing Vigilant Aerial Live Monitor (VALM) Server!")

    # Setup GPU
    if torch.cuda.is_available():
        state.device = "cuda"
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.enabled = True
        print(f"[GPU] Detected: {torch.cuda.get_device_name(0)}")
        print(f"[GPU] Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        state.device = "cpu"
        print("[WARN] CUDA not available, defaulting to CPU")

    torch.set_grad_enabled(False)

    model_path = "models/turtle.pt"
    state.model = await asyncio.to_thread(YOLO, model_path)
    await asyncio.to_thread(state.model.to, state.device)

    # Create tasks and store them so we can cancel them later
    inf_task = asyncio.create_task(inference_worker())
    ann_task = asyncio.create_task(annotation_worker())

    print(f"Server ready: http://{HOST}:{PORT}")
    print(f"WHIP endpoint: http://{HOST}:{PORT}/whip")

    print(f"Ready to receive WebRTC stream from OBS")

    yield  # --- SERVER RUNNING ---

    # --- SHUTDOWN ---

    # 1. Signal and cancel background workers
    state.stop_event.set()
    inf_task.cancel()
    ann_task.cancel()
    await asyncio.gather(inf_task, ann_task, return_exceptions=True)

    # 2. Close all WebSocket connections
    for ws in manager.active_connections:
        try:
            await ws.close()
        except Exception:
            pass

    # 3. Close WebRTC connection
    if state.pc:
        print("Closing WebRTC peer connection")
        try:
            await state.pc.close()
        except Exception as e:
            print(f"WebRTC close error: {e}")

    print("Workers have been stopped and all connections closed. Goodbye!")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whip_router)
app.include_router(inference_router)
app.include_router(annotation_router)
app.include_router(ws_router)

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info", ws="websockets")