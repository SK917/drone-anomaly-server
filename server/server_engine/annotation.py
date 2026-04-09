import asyncio
import cv2
from fastapi import APIRouter, Response, HTTPException
import server_engine.anomaly_det as anomaly_det
import server_engine.state as state
from server_engine.websocket_manager import manager

router = APIRouter()


@router.get("/annotated-frame.jpg")
async def get_annotated_frame():
    async with state.annotated_frame_lock:
        if state.latest_annotated_jpeg is None:
            raise HTTPException(status_code=404, detail="No Annotated Frame Found")
        updated_jpeg = state.latest_annotated_jpeg

    return Response(content=updated_jpeg, media_type="image/jpeg")

async def annotation_worker():
    print("Annotation Worker Initialized!")

    frame_counter = 0

    # this basically just runs until valm kills it. As new frames are processed by the inference worker
    # the annotation worker gathers them and annotates them.
    # this works pretty well since the inference worker can quickly jump to the next frame once its done with the current one
    # and the annotation worker doesn't take much time to annotate so the locks shouldn't cause issues with the inference worker (in theory)
    while not state.stop_event.is_set():

        # hard cap at 20fps for annotations.
        # TODO: Theres lowkey prolly a better way to handle this or just increase it
        await asyncio.sleep(0.05)  # ~20 FPS

        async with state.annotated_frame_lock:
            # TODO: Optimization tip I could probably just copy right away (not that it would make a huge differnece)
            frame = state.latest_raw_frame
            async with state.detections_lock:
                detections_copy = state.current_detections.copy()

        if frame is None:
            continue

        try:
            annotated = frame.copy()

            for det in detections_copy:
                x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
                track_id = det.get("track_id")

                # green for normal detections and red for anomalies
                is_anomaly = det.get("is_anomaly", False)
                color = (0, 0, 255) if is_anomaly else (0, 255, 0)

                label = f"{det['class_name']} {round(det['confidence']*100, 1)}%"

                if track_id is not None:
                    label = f"ID:{track_id} {label}"

                font = cv2.FONT_HERSHEY_DUPLEX
                font_scale = 0.6
                font_thickness = 2
                (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)

                cv2.rectangle(annotated, (x1, y1 - label_h - 10), (x1 + label_w, y1), color, -1)
                cv2.putText(annotated, label, (x1, y1 - 5), font, font_scale, (255, 255, 255), font_thickness)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                cv2.circle(annotated, anomaly_det.get_center(det["bbox"]), 1, color, 2)

            # encode the newely annotated frame as a JPEG for the front end to pull it
            # This can probably be optimized since we're probably saturating the network by sending full on JPEGs
            # At the moment this was the most stable way to get the frame from the server to the front end
            ret, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                async with state.annotated_frame_lock:
                    state.latest_annotated_jpeg = buffer.tobytes()

                if manager.active_connections:
                    frame_counter += 1
                    if frame_counter % 2 == 0:
                        await manager.broadcast({"type": "NEW_FRAME"})
                    # if frame_counter >= 4:
                        anomalies_snapshot = [d for d in detections_copy if d.get('is_anomaly', False)]

                        await manager.broadcast({
                            "type": "NEW_DATA",
                            "detections": detections_copy,
                            "timestamp": state.last_inference_time,
                            "num_detections": len(detections_copy),
                            "inference_count": state.inference_count,
                            "inference_fps": round(state.inference_fps, 2),
                            "has_anomaly": len(anomalies_snapshot) > 0,
                            "anomaly_count": len(anomalies_snapshot),
                            "stats": {
                                "inference_count": state.inference_count,
                                "inference_fps": round(state.inference_fps, 2),
                                "has_stream": state.ingest_video_track is not None,
                                "is_processing": state.is_inferencing,
                            },
                        })

                        if state.anomaly_update_pending:
                            await manager.broadcast({"type": "NEW_ANOMALY", "delta": state.anomaly_delta})
                            state.anomaly_update_pending = False
                            state.anomaly_delta = {"added": [], "updated": []}

                        frame_counter = 0
            else:
                print("Annotation Worker Failed To Encode JPEG")

        except Exception as e:
            print(f"Annotation Worker Error: {type(e).__name__}: {str(e)}")
