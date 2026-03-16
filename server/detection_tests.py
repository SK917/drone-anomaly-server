import ultralytics
from ultralytics import YOLO
from typing import Optional, Dict, Any, List
import numpy as np
import cv2
import torch
from PIL import Image
import anomaly_det
import time
import matplotlib.pyplot as plt

MODEL_PATH = "C:/Users/alexm/OneDrive/Desktop/School Code/Capstone Server/20260314_2Best.pt"
CONFIDENCE = 0.5
IMG_SIZE = 480
USE_FP16 = True # Enable Half Precision

# Define logic anomaly cases
# ANOMALY_CLASSES = ["bear", "cow"]
ANOMALY_CLASSES = ["pig", "fire", "wolf", "deer"]

model = YOLO(MODEL_PATH)

img = Image.open('C:/Users/alexm/OneDrive/Desktop/School Code/Capstone Server/server/crash.jpg')
img_array = np.array(img)

results = model.track(
        img_array, 
        imgsz=IMG_SIZE, 
        conf=CONFIDENCE, 
        device='cpu', 
        verbose=False,
        half=USE_FP16,
        agnostic_nms=True,
        tracker="bytetrack.yaml",
        persist=True
    )
for result in results:
    result.show()
start = time.perf_counter()

detections = anomaly_det.get_anomalies(results, ANOMALY_CLASSES, [6,6,10])

end = time.perf_counter()
print(end-start)
print(detections)

for det in detections:
    x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
    is_anomaly = det.get("is_anomaly", False)
    track_id = det.get("track_id")
    
    # Color: red for anomalies, green for normal
    color = (0, 0, 255) if is_anomaly else (0, 255, 0)
    thickness = 3 if is_anomaly else 2
    
    # Draw bounding box
    cv2.rectangle(img_array, (x1, y1), (x2, y2), color, thickness)
    
    # Label with track ID if available
    label = f"{det['class_name']} {det['confidence']*100:.1f}%"
    if track_id is not None:
        label = f"ID:{track_id} {label}"
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    font_thickness = 2
    (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
    cv2.rectangle(img_array, (x1, y1 - label_h - 10), (x1 + label_w, y1), color, -1)
    cv2.putText(img_array, label, (x1, y1 - 5), font, font_scale, (255, 255, 255), font_thickness)

plt.imshow(img_array)