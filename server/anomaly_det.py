from ultralytics import YOLO
from typing import Optional, Dict, Any, List
import math
import cv2
import numpy as np


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
            
            if "Traffic Jam" in anomaly_classes:
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
            
            if "Crowding" in anomaly_classes:
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
    if "Crowding" in anomaly_classes:
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
    if "Traffic Jam" in anomaly_classes:
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
    if "crash" in anomaly_classes:
        detections = check_crashes(detections)

    if "trespassing" in anomaly_classes:
        detections = check_tresspassing(detections, "cone")

    return detections

# return the center points of the bounding box
def get_center(bbox: List[4]) -> tuple:
    x1, y1, x2, y2 = bbox
    return round((x2+x1)/2), round((y2+y1)/2)

# checks the bounding boxes of cars from the input list and 
# adds a crash entry to the detections list if cars are too close
# together
def check_crashes(detections: List[Dict[str, Any]]):
    # get the list of cars and check how close their bounding boxes are to each other
    vehicles = []
    for det in detections:
        if det["class_name"] == "car" or det["class_name"] == "truck":
            vehicles.append(det)
    if not vehicles:
        return detections
    
    # sort vehicles by y1 position?
    quicksortDetections(vehicles, 0, len(vehicles)-1, "bbox")

    for i in range(len(vehicles)-1):
        # check distance between each coordinate and its successor
        # x1 to x1 and x2
        if vehicles[i]["bbox"][0] >= vehicles[i+1]["bbox"][0] and vehicles[i]["bbox"][0] <= vehicles[i+1]["bbox"][2]:
            # check y1 and y2 against successor's y1
            if vehicles[i]["bbox"][1] <= vehicles[i+1]["bbox"][1] and vehicles[i]["bbox"][3] >= vehicles[i+1]["bbox"][1]:
                x1 = vehicles[i+1]["bbox"][0]
                y1 = vehicles[i]["bbox"][1]
                # check i y2 vs i+1 y2
                if vehicles[i]["bbox"][3] < vehicles[i+1]["bbox"][3]:
                    y2 = vehicles[i+1]["bbox"][3]
                else:
                    y2 = vehicles[i]["bbox"][3]
                # check i x2 vs i+1 x2
                if vehicles[i]["bbox"][2] < vehicles[i+1]["bbox"][2]:
                    x2 = vehicles[i+1]["bbox"][2]
                else:
                    x2 = vehicles[i]["bbox"][2]
                #print(f"crash detected. car {vehicles[i]["track_id"]}'s x1 ({vehicles[i]["bbox"][0]}) overlaps with car {vehicles[i+1]["track_id"]}'s x1 ({vehicles[i+1]["bbox"][0]}) or x2 ({vehicles[i+1]["bbox"][2]})")
                detections.append({
                    "class_id": None,
                    "class_name": "Crash",
                    "confidence": 1,
                    "bbox": [x1,y1,x2,y2],
                    "track_id": None,
                    "is_anomaly": True
                })
        # compare x2 to x1 and x2
        elif vehicles[i]["bbox"][2] >= vehicles[i+1]["bbox"][0] and vehicles[i]["bbox"][2] <= vehicles[i+1]["bbox"][2]:
            if vehicles[i]["bbox"][1] <= vehicles[i+1]["bbox"][1] and vehicles[i]["bbox"][3] >= vehicles[i+1]["bbox"][1]:
                y1 = vehicles[i]["bbox"][1]
                # check i x1 vs i+1 x1
                if vehicles[i]["bbox"][0] < vehicles[i+1]["bbox"][0]:
                    x1 = vehicles[i]["bbox"][0]
                else:
                    x1 = vehicles[i+1]["bbox"][0]
                # check i y2 vs i+1 y2
                if vehicles[i]["bbox"][3] < vehicles[i+1]["bbox"][3]:
                    y2 = vehicles[i+1]["bbox"][3]
                else:
                    y2 = vehicles[i]["bbox"][3]
                # check i x2 vs i+1 x2
                if vehicles[i]["bbox"][2] < vehicles[i+1]["bbox"][2]:
                    x2 = vehicles[i+1]["bbox"][2]
                else:
                    x2 = vehicles[i]["bbox"][2]
                detections.append({
                    "class_id": None,
                    "class_name": "Crash",
                    "confidence": 1,
                    "bbox": [x1,y1,x2,y2],
                    "track_id": None,
                    "is_anomaly": True
                })
    
    return detections 

# takes in detections and the class label for markers.
# computes the center point of the detected markers and organizes them into
# clusters of points ordered by "closest point comes next". Presumably produces a vague polygon. hopefully.
def check_tresspassing(detections: List[Dict[str, Any]], marker_class):
    # grab list of detections with class name marker_class
    markers: List[Dict[str, Any]] = []
    for det in detections:
        if det["class_name"] == marker_class:
            markers.append(det)
            markers[len(markers)-1]["center"] = get_center(markers[len(markers)-1]["bbox"])
    
    if len(markers) == 0:
        return detections
    quicksortDetections(markers, 0, len(markers)-1, "center")
    # algo:
    # start at markers[0]. get distance to every other marker in the array
    # move closest marker to position marker[1]
    # check distance to every other marker in the array at position > 1
    # move closest marker to position marker[2], so on
    # once the array is sorted, go through one more time and check distances between markers
    # if the distance between 2 markers is significantly greater than the average distances between the other markers before it, consider it a separate cluster

    mean = 0
    standard_dev = 0
    for i in range(len(markers)-1):
        closest = [99999,0]
        for j in range(i+1, len(markers)): # inefficient. O(n^2) (╥﹏╥)
            dx: int = markers[i]["center"][0] - markers[j]["center"][0]
            dy: int = markers[i]["center"][1] - markers[j]["center"][1]
            if math.sqrt(dx**2 + dy**2) < closest[0]:
                closest = [math.sqrt(dx**2 + dy**2), j]
        # swap i+1 with closest
        mean += closest[0]
        temp = markers[i+1]
        markers[i+1] = markers[closest[1]]
        markers[closest[1]] = temp
    
    clusters: List[List[Dict[str, Any]]] = []

    mean = mean/len(markers)

    next_cluster_start = 0
    for i in range(len(markers)-1):
        dx = markers[i]["center"][0] - markers[i+1]["center"][0]
        dy = markers[i]["center"][1] - markers[i+1]["center"][1]
        if math.sqrt(dx**2 + dy**2) >= mean * 2:
            # denotes a new cluster of markers
            clusters.append(markers[next_cluster_start:i+1])
            next_cluster_start = i+1
        if i == len(markers)-2:
            clusters.append(markers[next_cluster_start:i+1])

    for c in clusters:
        for i in range(len(c)):
            if i < len(c)-1:
                c[i]["next_vector"] = c[i+1]["center"]
            else:
                c[i]["next_vector"] = c[0]["center"]
            for det in detections:
                if det["track_id"] == c[i]["track_id"]:
                    det["next_vector"] = c[i]["next_vector"]

    # clusters[] now holds clusters of markers, organized by closest points.
    # next, use cv2's point polygon test to check if each detected person is in a cluster.
    for det in detections:
        if det["class_name"] == "person":
            for c in clusters:
                points: List[List] = []
                for marker in c:
                    points.append(marker["center"])
                print(cv2.pointPolygonTest(np.array(points), get_center(det["bbox"]), False))
                if cv2.pointPolygonTest(np.array(points), get_center(det["bbox"]), False) > 0:
                    # calculate bounding box
                    bbox = get_cluster_bbox(c)
                    # add a trespassing anomaly to detections
                    detections.append({
                    "class_id": None,
                    "class_name": "trespassing",
                    "confidence": 1,
                    "bbox": bbox,
                    "track_id": None,
                    "is_anomaly": True
                })
    
    return detections
    

def get_cluster_bbox(cluster: List[Dict[str, Any]]) -> List[4]:
    x1 = 9999999
    x2 = 0
    y1 = 9999999
    y2 = 0
    for c in cluster:
        if c["center"][0] < x1:
            x1 = c["center"][0]
        if c["center"][0] > x2:
            x2 = c["center"][0]
        if c["center"][1] < y1:
            y1 = c["center"][1]
        if c["center"][1] > y2:
            y2 = c["center"][1]
    return [x1,y1,x2,y2]

def quicksortDetections(detections, low, high, sortMetric):
    v = []
    if low < high:
        pi = partition(detections, low, high, sortMetric)
        quicksortDetections(detections, pi+1, high, sortMetric) 
        quicksortDetections(detections, low, pi-1, sortMetric)     

def partition(detections, low, high, sortMetric):
    if sortMetric == "bbox":
        pivot = detections[high]["bbox"][1]
        i = low-1
        for j in range(low, high):
            if detections[j]["bbox"][1] < pivot:
                i += 1
                swap(detections, i, j)
        swap(detections, i+1, high)
        return i+1
    elif sortMetric == "center":
        pivot = detections[high]["center"][1]
        i = low-1
        for j in range(low, high):
            if detections[j]["center"][1] < pivot:
                i += 1
                swap(detections, i, j)
        swap(detections, i+1, high)
        return i+1

def swap(detections, i, j):
    detections[i], detections[j] = detections[j], detections[i]

