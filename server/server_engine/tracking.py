import warnings
import numpy as np
from boxmot import OcSort

class HybridTracker:
    def __init__(self):
        # det_thresh: Minimum confidence to be considered for tracking.
        # (Since our detections are already 35%+ this setting actually doesn't filter anything out but I manually set it to 0.1 just to make sure toggling the confidence wont cause problems)
        # max_age: Maximum number of frames to keep a track alive. We can increase it if objects disappear and re-appear for longer but my testing showed no object was ever gone for more than like 25 frames or so
        # min_hits: Minimum number of detections before a track is assigned. Since we want an ID ASAP I set this to 0 but we can make it 1 if IDs are too jumpy
        # iou_threshold: IOU threshold for matching detections to tracks. Set to 0.2 (slightly lower than YOLO) I lowered it to make track matching easier
        self.tracker = OcSort(det_thresh=0.1, max_age=40, min_hits=0, iou_threshold=0.2)

        # Starting ID for dummy IDs
        self.next_id = 90000

    def reset(self):
        self.__init__()

    def update(self, detections):
        if not detections:
            return []

        dets = []

        for d in detections:
            d["track_id"] = None
            x1, y1, x2, y2 = d["bbox"]
            dets.append([float(x1), float(y1), float(x2), float(y2), float(d.get("confidence", 1.0)), float(d["class_id"])])

        dets = np.array(dets, dtype=np.float32)

        tracks = self.tracker.update(dets)

        matched = set()

        if tracks is not None and len(tracks):
            for track in tracks:
                # track index
                det_idx = int(track[7])

                # track ID
                track_id = int(track[4])

                # move the tracking IDs back into the detections dict
                if 0 <= det_idx < len(detections):
                    detections[det_idx]["track_id"] = track_id
                    matched.add(det_idx)

        # this is the fall back. If for whatever reason no ID was given then we'll assign a dummy one (This one changes every frame which kinda sucks
        # but the tracker is super permissive so it shouldn't happen often at all)
        for i, d in enumerate(detections):
            if i not in matched:
                d["track_id"] = self.next_id
                self.next_id += 1

        return detections


tracker = HybridTracker()