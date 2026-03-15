import ultralytics
from ultralytics import YOLO
from typing import Optional, Dict, Any, List
import numpy as np
import cv2
import torch
from PIL import Image
import anomaly_det
import time

MODEL_PATH = "yolo11s.pt"
CONFIDENCE = 0.5
IMG_SIZE = 480
USE_FP16 = True # Enable Half Precision

# Define logic anomaly cases
# ANOMALY_CLASSES = ["bear", "cow"]
ANOMALY_CLASSES = ["pig", "fire", "wolf", "deer"]

model = YOLO("C:/Users/alexm/OneDrive/Desktop/School Code/Capstone Server/noMarkingsDodo.pt")

img = Image.open('C:/Users/alexm/OneDrive/Desktop/School Code/Capstone Server/server/Screenshot 2026-03-07 191200.jpg')
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
#print(detections)