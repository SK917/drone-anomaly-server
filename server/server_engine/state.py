import asyncio
from typing import Optional, Dict, Any, List
import numpy as np
import aiortc
from ultralytics import YOLO

# WebRTC stuff
pc: Optional[aiortc.RTCPeerConnection] = None
ingest_video_track = None

# YOLO stuff
model: Optional[YOLO] = None
device: str = "cpu"
inference_count: int = 0
last_inference_time: float = 0.0
inference_fps: float = 0.0

# detection and frame info between inference and annotation worker and events
stop_event = asyncio.Event()
is_inferencing: bool = False
latest_raw_frame: Optional[np.ndarray] = None
latest_annotated_jpeg: Optional[bytes] = None
annotated_frame_lock = asyncio.Lock()
current_detections: List[Dict[str, Any]] = []
detections_lock = asyncio.Lock()

# Anomalies list
anomalies_list: List[Dict[str, Any]] = []
anomalies_by_track_id: Dict[int, Dict[str, Any]] = {}
seen_anomaly_ids: set[int] = set()
anomalies_lock = asyncio.Lock()
anomaly_update_pending: bool = False
anomaly_delta: Dict[str, Any] = {"added": [], "updated": []}
