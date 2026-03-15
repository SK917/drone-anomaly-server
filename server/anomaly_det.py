from ultralytics import YOLO
from typing import Optional, Dict, Any, List


# Flags anomalies based off detection inputs
# Outputs list of detections with is_anomaly set to true
def get_anomalies(yolo_output, anomaly_classes, thresholds: List):
    detections: List[Dict[str, Any]] = []
    people_count = 0
    crowd_box = [None, None, None, None]
    vehicle_count = 0
    traffic_box = [None, None, None, None]

    for det in yolo_output:
        names = getattr(det, "names", {})
        boxes = det.boxes
        if boxes is None:
            continue
        
        for b in boxes:
            obj_class = int(b.cls[0])
            confidence = float(b.conf[0])
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            class_name = names.get(obj_class, str(obj_class))
            
            track_id = None
            if hasattr(b, 'id') and b.id is not None:
                track_id = int(b.id[0])
            # Class based anomalies
            is_anomaly = class_name.lower() in [anomaly.lower() for anomaly in anomaly_classes]
            
            # Traffic Jam
            if class_name == "car" or class_name == "truck":
                vehicle_count += 1
                if traffic_box[0] == None: # x1
                    traffic_box[0] = x1
                elif x1 < traffic_box[0]:
                    traffic_box[0] = x1
                if traffic_box[1] == None: # y1
                    traffic_box[1] = y1
                elif y1 < traffic_box[1]:
                    traffic_box[1] = y1
                if traffic_box[2] == None: # x2
                    traffic_box[2] = x2
                elif x2 > traffic_box[2]:
                    traffic_box[2] = x2
                if traffic_box[3] == None: # y2
                    traffic_box[3] = y2
                elif y2 > traffic_box[3]:
                    traffic_box[3] = y2
                
            # Crowding
            if class_name == "person":
                people_count += 1
                if crowd_box[0] == None: # x1
                    crowd_box[0] = x1
                elif x1 < crowd_box[0]:
                    crowd_box[0] = x1
                if crowd_box[1] == None: # y1
                    crowd_box[1] = y1
                elif y1 < crowd_box[1]:
                    crowd_box[1] = y1
                if crowd_box[2] == None: # x2
                    crowd_box[2] = x2
                elif x2 > crowd_box[2]:
                    crowd_box[2] = x2
                if crowd_box[3] == None: # y2
                    crowd_box[3] = y2
                elif y2 > crowd_box[3]:
                    crowd_box[3] = y2
            
            detections.append({
                "class_id": obj_class,
                "class_name": class_name,
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2],
                "track_id": track_id,
                "is_anomaly": is_anomaly
            })
    # Crowding
    if people_count >= thresholds[0]:
        detections.append({
                "class_id": None,
                "class_name": "Crowding",
                "confidence": 1,
                "bbox": crowd_box,
                "track_id": track_id,
                "is_anomaly": True
            })
    # Traffic Jam
    if vehicle_count >= thresholds[1]:
        detections.append({
                "class_id": None,
                "class_name": "Traffic Jam",
                "confidence": 1,
                "bbox": traffic_box,
                "track_id": track_id,
                "is_anomaly": True
            })
    detections = check_crashes(detections, thresholds[2])

    return detections

# return the center points of the bounding box
def get_center(bbox: List[4]) -> tuple:
    x1, y1, x2, y2 = bbox
    return round((x2+x1)/2), round((y2+y1)/2)

# checks the bounding boxes of cars from the input list and 
# adds a crash entry to the detections list if cars are too close
# together
def check_crashes(detections: List[Dict[str, Any]], thresh):
    # get the list of cars and check how close their bounding boxes are to each other
    vehicles = []
    for det in detections:
        if det["class_name"] == "car" or det["class_name"] == "truck":
            vehicles.append(det)
    if not vehicles:
        return detections
    
    # sort vehicles by y1 position?
    quicksortVehicles(vehicles, 0, len(vehicles)-1)

    for i in range(len(vehicles)-1):
        # check distance between each coordinate and its successor
        # x1 to x1 and x2
        if abs(vehicles[i]["bbox"][0] - vehicles[i+1]["bbox"][0]) < thresh or abs(vehicles[i]["bbox"][0] - vehicles[i+1]["bbox"][2]) < thresh:
            # check y1 against y1 and y2
            if abs(vehicles[i]["bbox"][1] - vehicles[i+1]["bbox"][1]) < thresh or abs(vehicles[i]["bbox"][1] - vehicles[i+1]["bbox"][3]) < thresh:
                if vehicles[i]["bbox"][0] < vehicles[i+1]["bbox"][0]:
                    x1 = vehicles[i]["bbox"][0]
                else:
                    x1 = vehicles[i+1]["bbox"][0]
                if vehicles[i]["bbox"][2] < vehicles[i+1]["bbox"][2]:
                    x2 = vehicles[i+1]["bbox"][2]
                else:
                    x2 = vehicles[i]["bbox"][2]
                detections.append({
                    "class_id": None,
                    "class_name": "Crash",
                    "confidence": 1,
                    "bbox": [x1,vehicles[i]["bbox"][1], x2,vehicles[i+1]["bbox"][3]],
                    "track_id": None,
                    "is_anomaly": True
                })
            # check y2 against y1 and y2
            elif abs(vehicles[i]["bbox"][3] - vehicles[i+1]["bbox"][1]) < thresh or abs(vehicles[i]["bbox"][3] - vehicles[i+1]["bbox"][3]) < thresh:
                if vehicles[i]["bbox"][0] < vehicles[i+1]["bbox"][0]:
                    x1 = vehicles[i]["bbox"][0]
                else:
                    x1 = vehicles[i+1]["bbox"][0]
                if vehicles[i]["bbox"][2] < vehicles[i+1]["bbox"][2]:
                    x2 = vehicles[i+1]["bbox"][2]
                else:
                    x2 = vehicles[i]["bbox"][2]
                detections.append({
                    "class_id": None,
                    "class_name": "Crash",
                    "confidence": 1,
                    "bbox": [x1,vehicles[i]["bbox"][1], x2,vehicles[i+1]["bbox"][3]],
                    "track_id": None,
                    "is_anomaly": True
                })

        # x2 to x1 and x2
        elif abs(vehicles[i]["bbox"][2] - vehicles[i+1]["bbox"][0]) < thresh or abs(vehicles[i]["bbox"][2] - vehicles[i+1]["bbox"][2]):
            # check y1 against y1 and y2
            if abs(vehicles[i]["bbox"][1] - vehicles[i+1]["bbox"][1]) < thresh or abs(vehicles[i]["bbox"][1] - vehicles[i+1]["bbox"][3]) < thresh:
                if vehicles[i]["bbox"][0] < vehicles[i+1]["bbox"][0]:
                    x1 = vehicles[i]["bbox"][0]
                else:
                    x1 = vehicles[i+1]["bbox"][0]
                if vehicles[i]["bbox"][2] < vehicles[i+1]["bbox"][2]:
                    x2 = vehicles[i+1]["bbox"][2]
                else:
                    x2 = vehicles[i]["bbox"][2]
                detections.append({
                    "class_id": None,
                    "class_name": "Crash",
                    "confidence": 1,
                    "bbox": [x1,vehicles[i]["bbox"][1], x2,vehicles[i+1]["bbox"][3]],
                    "track_id": None,
                    "is_anomaly": True
                })
            # check y2 against y1 and y2
            elif abs(vehicles[i]["bbox"][3] - vehicles[i+1]["bbox"][1]) < thresh or abs(vehicles[i]["bbox"][3] - vehicles[i+1]["bbox"][3]) < thresh:
                if vehicles[i]["bbox"][0] < vehicles[i+1]["bbox"][0]:
                    x1 = vehicles[i]["bbox"][0]
                else:
                    x1 = vehicles[i+1]["bbox"][0]
                if vehicles[i]["bbox"][2] < vehicles[i+1]["bbox"][2]:
                    x2 = vehicles[i+1]["bbox"][2]
                else:
                    x2 = vehicles[i]["bbox"][2]
                detections.append({
                    "class_id": None,
                    "class_name": "Crash",
                    "confidence": 1,
                    "bbox": [x1,vehicles[i]["bbox"][1], x2,vehicles[i+1]["bbox"][3]],
                    "track_id": None,
                    "is_anomaly": True
                })
    
    return detections

    

def quicksortVehicles(vehicles, low, high):
    v = []
    if low < high:
        pi = partition(vehicles, low, high)
        quicksortVehicles(vehicles, pi+1, high) 
        quicksortVehicles(vehicles, low, pi-1)
        
        

def partition(vehicles, low, high):
    pivot = vehicles[high]["bbox"][1]
    i = low-1
    v = []
    for j in range(low, high):
        if vehicles[j]["bbox"][1] < pivot:
            i += 1
            swap(vehicles, i, j)
    swap(vehicles, i+1, high)
    return i+1

def swap(vehicles, i, j):
    vehicles[i], vehicles[j] = vehicles[j], vehicles[i]