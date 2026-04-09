import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np
from fastapi import APIRouter
import server_engine.anomaly_det as anomaly_det
import server_engine.state as state
from server_engine.tracking import tracker
from server_engine.websocket_manager import manager

router = APIRouter()

@router.get("/detections")
async def get_detections():
    async with state.detections_lock:
        anomalies = [d for d in state.current_detections if d.get('is_anomaly', False)]
        return {
            "timestamp": state.last_inference_time,
            "num_detections": len(state.current_detections),
            "detections": state.current_detections,
            "inference_count": state.inference_count,
            "inference_fps": round(state.inference_fps, 2),
            "has_anomaly": len(anomalies) > 0,
            "anomaly_count": len(anomalies),
        }

@router.get("/anomalies")
async def get_anomalies():
    async with state.anomalies_lock:
        anomalies_copy = state.anomalies_list.copy()

    classes = {}
    for a in anomalies_copy:
        cid = a["class_id"]
        cname = a["class_name"]
        if cid not in classes:
            classes[cid] = {"class_id": cid, "class_name": cname}

    return {
        "count": len(anomalies_copy),
        "classes": list(classes.values()),
        "anomalies": anomalies_copy,
    }

@router.get("/stats")
async def get_stats():
    return {
        "inference_count": state.inference_count,
        "inference_fps": round(state.inference_fps, 2),
        "has_stream": state.ingest_video_track is not None,
        "is_processing": state.is_inferencing,
    }

# Use ultralytics built in tracking support with custom bytetrack algorithm
def _run_yolo_on_frame(frame_bgr: np.ndarray) -> tuple[List[Dict[str, Any]], float]:
    # TODO: UPDATE THIS TO ADD ANOMALIESSSSS
    anomaly_classes = state.anomaly_classes

    # image size 640 because the larger it gets the slower inference gets and it seems good enough for detections
    # the model I am trainig is also being trainned on 640 to match this so if we do change it I'll retrain it.
    img_size = 640

    # The model is a bit conservative so we need to lower the confidence to ensure things get detected
    confidence = 0.5

    # Half precision speeds up inference without really tanking accuracy (since our laptops use Nvidia chips)
    # We can toggle this though to see if it helps catch some detections
    use_fp16 = True

    t0 = time.time()

    # iou : I set this to 0.3 to aggressively filter overalpping or duplicate boxes (we can increase it if we want)
    _iou = 0.3

    # device : Should be the GPU but defaults to CPU
    # agnostic_nms : I'm using this to avoid different classes claiming he same object (we can probably remove this though since the model is better) only problem is it might cause detections to be missed (will do more tests before demo)
    # persist : keeps the tracker ids
    #results = state.model.track(frame_bgr, imgsz=img_size, conf=confidence, device=state.device, verbose=False, half=use_fp16, agnostic_nms=False, iou=_iou, tracker='botsort.yaml', persist=True)
    results = state.model.predict(frame_bgr, imgsz=img_size, conf=confidence, device=state.device, verbose=False, half=use_fp16, agnostic_nms=False, iou=_iou)

    infms = (time.time() - t0) * 1000.0

    # filter out broken detections (only needed because the model is a bit buggy still)
    # I'll keep this in for the demo just in case but the model has imrpoved a bit.
    results = filter_invalid_bboxes(results)

    # send to the logic based anomaly detector
    detections = anomaly_det.get_anomalies(results, anomaly_classes, [8, 8, 1])
    detections = tracker.update(detections, frame_bgr)

    return detections, infms

def debug_print_bbox_sizes(detections: List[Dict[str, Any]]) -> None:
    for i, det in enumerate(detections, 1):
        bbox = det.get("bbox")
        if not bbox or len(bbox) != 4:
            print(f"  {i}. invalid bbox -> {bbox}")
            continue
        x1, y1, x2, y2 = bbox
        width = max(0.0, float(x2) - float(x1))
        height = max(0.0, float(y2) - float(y1))
        area = width * height
        class_name = det.get("class_name", "unknown")
        track_id = det.get("track_id")
        track_text = f"ID:{track_id} " if track_id is not None else ""
        print(f"\t{i}. {track_text}{class_name}: {width:.1f} x {height:.1f} px (area={area:.1f})")

# This is kind of a fail safe for our model since it still has those weird detections
# The bounding boxes are just ad hoc (I based them on the validation set testing BB sizes)
def filter_invalid_bboxes(results) -> List[Dict[str, Any]]:
    min_bbox = {"min_w": 5, "min_h": 5}

    bbox_size_limits = {
        "car": {"max_w": 400, "max_h": 400},
        "police_car": {"max_w": 400, "max_h": 400},
        "person": {"max_w": 250, "max_h": 250},
        "wolf": {"max_w": 250, "max_h": 250},
        "pig": {"max_w": 250, "max_h": 250},
        "deer": {"max_w": 250, "max_h": 250},
        "fire": {"max_w": 400, "max_h": 400},
        "cone": {"max_w": 150, "max_h": 150},
    }

    for det in results:
        boxes = det.boxes
        if boxes is None:
            continue
        names = getattr(det, "names", {})
        keep = []

        for i, b in enumerate(boxes):
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            w = x2 - x1
            h = y2 - y1
            class_name = names.get(int(b.cls[0]), str(int(b.cls[0])))
            min_w = min_bbox["min_w"]
            min_h = min_bbox["min_h"]

            if w < min_w or h < min_h:
                continue

            limits = bbox_size_limits.get(class_name)
            if limits is not None:
                max_w = limits["max_w"]
                max_h = limits["max_h"]

                if w > max_w or h > max_h:
                    continue

            keep.append(i)
        if len(keep) < len(boxes):
            det.boxes = boxes[keep]
    return results

# Inference Worker
async def inference_worker():
    """
    Continuously pull frames from WebRTC and run inference.
    Drops all buffered frames - only processes the latest frame.
    """
    inference_start_time = None

    # Avoid bowing up the terminal
    log_every = 20

    # enables debug info
    debug = False

    print("Inference Worker Initialized!")

    # this basically just runs until valm kills it. As new frames come in from the stream
    # thie inference worker grabs the latest frame and runs inference which avoids the issue where the stream and server timings
    # diverge as a backlog of frames comes in (since the inference server runs slower than the stream). *I thinks its 30fps vs 20fps rn
    while not state.stop_event.is_set():
        await asyncio.sleep(0.001)  # Small sleep to prevent busy-wait

        # Wait for stream
        if state.ingest_video_track is None:
            await asyncio.sleep(0.1)
            continue

        # Skip if already processing (prevents concurrent inference)
        if state.is_inferencing:
            continue

        state.is_inferencing = True

        try:
            latest_frame = None
            frames_drained = 0

            # when the server is inferencing the video track fills a backlog of frames. We need to flush it by looping over the backlog and only keeping the frame
            # right before the draining times out. Essentially only keeping the newest frame
            # the timeout is set super low to avoid new frames adding to the backlog and then us basically waiting forever.
            while True:
                try:
                    frame = await asyncio.wait_for(state.ingest_video_track.recv(), timeout=0.001)
                    latest_frame = frame
                    frames_drained += 1
                except asyncio.TimeoutError:
                    break

            if latest_frame is None:
                state.is_inferencing = False
                continue

            # should be around 3-4 frames
            if frames_drained > 1 and state.inference_count % log_every == 0 and debug:
                print(f"Drained {frames_drained} Frames")

            img = latest_frame.to_ndarray(format="bgr24")

            # inference and anomaly detetion
            # using here asyncio.to_thread to allow annotation and websocket workers to continue running while inference is occuring
            detections, infer_ms = await asyncio.to_thread(_run_yolo_on_frame, img)

            # TODO: comment this out in demo
            # debug_print_bbox_sizes(detections)

            state.inference_count += 1
            current_time = time.time()

            if inference_start_time is None:
                inference_start_time = current_time

            elapsed = current_time - inference_start_time
            state.inference_fps = state.inference_count / elapsed if elapsed > 0 else 0.0
            state.last_inference_time = current_time

            # update the shared frame and detections info for the annotation worker to pickup
            async with state.annotated_frame_lock:
                state.latest_raw_frame = img
                async with state.detections_lock:
                    state.current_detections = detections

            anomalies = [d for d in detections if d.get('is_anomaly', False)]

            # Update anomalies list, broadcast new entries
            # Only updates if there are connected clients
            if manager.active_connections:
                added_entries: List[Dict[str, Any]] = []
                updated_entries: List[Dict[str, Any]] = []

                async with state.anomalies_lock:
                    for det in anomalies:
                        track_id = det.get("track_id")
                        if track_id is None:
                            continue

                        existing_entry = state.anomalies_by_track_id.get(track_id)

                        if existing_entry is None:
                            state.seen_anomaly_ids.add(track_id)
                            new_entry = det.copy()
                            new_entry["timestamp"] = time.time()
                            state.anomalies_list.append(new_entry)
                            state.anomalies_by_track_id[track_id] = new_entry
                            added_entries.append(new_entry)

                        elif det["confidence"] > existing_entry["confidence"]:
                            existing_entry["confidence"] = det["confidence"]
                            existing_entry["bbox"] = det["bbox"]
                            updated_entries.append({
                                "track_id": track_id,
                                "confidence": det["confidence"],
                                "bbox": det["bbox"],
                            })

                if added_entries or updated_entries:
                    state.anomaly_update_pending = True
                    state.anomaly_delta["added"].extend(added_entries)
                    for update in updated_entries:
                        existing = next(
                            (u for u in state.anomaly_delta["updated"] if u["track_id"] == update["track_id"]),
                            None,
                        )
                        if existing:
                            existing["confidence"] = update["confidence"]
                            existing["bbox"] = update["bbox"]
                        else:
                            state.anomaly_delta["updated"].append(update)
            else:
                # Clear history if no one is watching to keep session fresh
                if state.seen_anomaly_ids:
                    state.seen_anomaly_ids.clear()
                    async with state.anomalies_lock:
                        state.anomalies_list.clear()
                        state.anomalies_by_track_id.clear()

            if detections and state.inference_count % log_every == 0 and debug:
                print(f"\n[INFERENCE #{state.inference_count}] @ {state.inference_fps:.1f} FPS - Found {len(detections)} object(s) ({infer_ms:.1f}ms):")
                for i, d in enumerate(detections, 1):
                    print(f"  {i}. {d['class_name']} ({d['confidence']*100:.1f}%)")
            elif not detections and state.inference_count % log_every == 0 and debug:
                print(f"[INFERENCE #{state.inference_count}] @ {state.inference_fps:.1f} FPS - No objects detected ({infer_ms:.1f}ms)")

            if anomalies and debug:
                print(f"ANOMALY: {', '.join([a['class_name'] for a in anomalies])}")

        except Exception as e:
            print(f"Inference Worker Error: {type(e).__name__}: {str(e)[:100]}")
        finally:
            state.is_inferencing = False