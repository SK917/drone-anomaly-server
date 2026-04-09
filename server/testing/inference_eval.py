import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import torch
from ultralytics import YOLO

import server_engine.state as state
from server_engine.inference import _run_yolo_on_frame


DEFAULT_TEST_IMAGES_DIR = Path(__file__).resolve().parent / "test_images"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
OUTPUT_DIR_NAME = "output"


def annotate_detections_on_image(frame: Any, detections: List[Dict[str, Any]]) -> Any:
    annotated = frame.copy()
    for detection in detections:
        bbox = detection.get("bbox")
        if not bbox or len(bbox) != 4:
            continue

        x1, y1, x2, y2 = [int(v) for v in bbox]
        is_anomaly = bool(detection.get("is_anomaly", False))
        class_name = str(detection.get("class_name", "unknown"))
        confidence = detection.get("confidence")

        color = (0, 0, 255) if is_anomaly else (0, 255, 0)
        thickness = 3 if is_anomaly else 2
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

        track_id = detection.get("track_id")
        track_prefix = f"#{track_id} " if track_id is not None else ""

        if isinstance(confidence, (float, int)):
            label = f"{track_prefix}{class_name} {float(confidence):.2f}"
        else:
            label = f"{track_prefix}{class_name}"

        label_y = max(15, y1 - 8)
        cv2.putText(annotated, label, (x1, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    return annotated

def load_class_names(classes_path: Path, model: YOLO) -> Dict[int, str]:
    if classes_path.exists():
        with classes_path.open("r", encoding="utf-8") as f:
            names = [line.strip() for line in f if line.strip()]
        return {i: name for i, name in enumerate(names)}

    model_names = getattr(model, "names", {})
    if isinstance(model_names, dict):
        return {int(k): str(v) for k, v in model_names.items()}
    if isinstance(model_names, list):
        return {i: str(name) for i, name in enumerate(model_names)}
    return {}


def parse_yolo_labels_for_single_image(
    label_path: Path,
    image_w: int,
    image_h: int,
    class_map: Dict[int, str],
    anomaly_class_set: set,
) -> Dict[str, List[Dict[str, Any]]]:
    objects: List[Dict[str, Any]] = []
    anomalies: List[Dict[str, Any]] = []

    if not label_path.exists():
        return {"objects": objects, "anomalies": anomalies}

    with label_path.open("r", encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p for p in line.split() if p]
            if len(parts) < 5:
                raise ValueError(
                    f"Invalid YOLO label line {line_num} in {label_path.name}: "
                    "expected class_id x_center y_center width height"
                )

            class_id = int(float(parts[0]))
            xc = float(parts[1])
            yc = float(parts[2])
            bw = float(parts[3])
            bh = float(parts[4])

            # Support normalized YOLO values and absolute-pixel variants.
            if xc <= 1.0 and yc <= 1.0 and bw <= 1.0 and bh <= 1.0:
                xc *= image_w
                yc *= image_h
                bw *= image_w
                bh *= image_h

            x1 = max(0.0, xc - bw / 2.0)
            y1 = max(0.0, yc - bh / 2.0)
            x2 = min(float(image_w), xc + bw / 2.0)
            y2 = min(float(image_h), yc + bh / 2.0)

            class_name = class_map.get(class_id, str(class_id))
            entry = {"class_name": class_name, "bbox": [x1, y1, x2, y2]}
            objects.append(entry)
            if class_name.lower() in anomaly_class_set:
                anomalies.append(entry)

    return {"objects": objects, "anomalies": anomalies}


def match_counts(
    predictions: List[Dict[str, Any]],
    ground_truths: List[Dict[str, Any]],
) -> Tuple[int, int, int]:
    # Simpler metric: match by class counts only (ignores box overlap quality).
    pred_counts: Dict[str, int] = {}
    gt_counts: Dict[str, int] = {}

    for prediction in predictions:
        class_name = str(prediction.get("class_name", "")).lower()
        if class_name:
            pred_counts[class_name] = pred_counts.get(class_name, 0) + 1

    for ground_truth in ground_truths:
        class_name = str(ground_truth.get("class_name", "")).lower()
        if class_name:
            gt_counts[class_name] = gt_counts.get(class_name, 0) + 1

    true_positives = 0
    false_positives = 0
    false_negatives = 0

    all_classes = set(pred_counts.keys()) | set(gt_counts.keys())
    for class_name in all_classes:
        pred_n = pred_counts.get(class_name, 0)
        gt_n = gt_counts.get(class_name, 0)
        true_positives += min(pred_n, gt_n)
        false_positives += max(0, pred_n - gt_n)
        false_negatives += max(0, gt_n - pred_n)

    return true_positives, false_positives, false_negatives


def compute_precision_recall_f1(true_positives: int, false_positives: int, false_negatives: int) -> Tuple[float, float, float]:
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def init_hybrid_server_model(model_path: str) -> None:
    state.device = "cuda" if torch.cuda.is_available() else "cpu"
    state.model = YOLO(model_path)
    state.model.to(state.device)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate hybrid_server inference on YOLO-format labeled images")
    parser.add_argument("--model", default="../models/ant.pt", help="Model path override")
    args = parser.parse_args()

    images_dir = DEFAULT_TEST_IMAGES_DIR
    labels_dir = DEFAULT_TEST_IMAGES_DIR
    classes_path = labels_dir / "classes.txt"

    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    if not labels_dir.exists():
        raise FileNotFoundError(f"Labels directory not found: {labels_dir}")

    print(f"Using images directory: {images_dir}")
    print(f"Using labels directory: {labels_dir}")
    if classes_path.exists():
        print(f"Using classes file: {classes_path}")

    init_hybrid_server_model(args.model)
    class_map = load_class_names(classes_path, state.model)
    anomaly_class_set = {"pig", "fire", "wolf", "deer"}

    tp_obj = fp_obj = fn_obj = 0
    tp_ano = fp_ano = fn_ano = 0
    total_ms = 0.0
    processed = 0
    missing_images: List[str] = []

    output_dir = images_dir / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    image_files = []
    for image_path in sorted(images_dir.rglob("*")):
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        # Skip previously generated annotation outputs
        if output_dir in image_path.parents:
            continue
        image_files.append(image_path)

    if not image_files:
        raise ValueError(
            f"No images found in {images_dir}. "
            f"Supported extensions: {sorted(IMAGE_EXTENSIONS)}"
        )

    t_start = time.time()

    for image_path in image_files:
        file_name = image_path.name
        frame = cv2.imread(str(image_path))
        if frame is None:
            missing_images.append(file_name)
            continue

        image_h, image_w = frame.shape[:2]
        # 1) Label beside image (common in quick test sets)
        # 2) Label under labels_dir root
        # 3) Fallback recursive lookup by stem (useful for nested dataset layouts)
        label_path = image_path.with_suffix(".txt")
        if not label_path.exists():
            label_path = labels_dir / f"{image_path.stem}.txt"
        if not label_path.exists():
            candidates = list(labels_dir.rglob(f"{image_path.stem}.txt"))
            if candidates:
                label_path = candidates[0]

        gt = parse_yolo_labels_for_single_image(label_path, image_w, image_h, class_map, anomaly_class_set)

        detections, infer_ms = _run_yolo_on_frame(frame)
        total_ms += infer_ms
        processed += 1

        relative_image_path = image_path.relative_to(images_dir)
        output_image_path = output_dir / relative_image_path
        output_image_path.parent.mkdir(parents=True, exist_ok=True)
        annotated = annotate_detections_on_image(frame, detections)
        cv2.imwrite(str(output_image_path), annotated)

        gt_objects = gt.get("objects", [])
        gt_anomalies = gt.get("anomalies", [])

        # Object detections only (exclude aggregate/synthetic anomalies like Crowding/Crash)
        pred_objects = [d for d in detections if d.get("class_id") is not None]

        # All anomaly outputs (class-based and synthetic)
        pred_anomalies = [d for d in detections if d.get("is_anomaly", False)]

        obj_tp, obj_fp, obj_fn = match_counts(pred_objects, gt_objects)
        ano_tp, ano_fp, ano_fn = match_counts(pred_anomalies, gt_anomalies)

        tp_obj += obj_tp
        fp_obj += obj_fp
        fn_obj += obj_fn

        tp_ano += ano_tp
        fp_ano += ano_fp
        fn_ano += ano_fn

    elapsed = time.time() - t_start

    p_obj, r_obj, f1_obj = compute_precision_recall_f1(tp_obj, fp_obj, fn_obj)
    p_ano, r_ano, f1_ano = compute_precision_recall_f1(tp_ano, fp_ano, fn_ano)

    avg_ms = total_ms / processed if processed > 0 else 0.0
    avg_fps = 1000.0 / avg_ms if avg_ms > 0 else 0.0

    print("\n=== Inference Evaluation Summary ===")
    print(f"Images found: {len(image_files)}")
    print(f"Images processed: {processed}")
    print(f"Missing/unreadable images: {len(missing_images)}")

    print("\n--- Object Detection Metrics ---")
    print(f"True Positives:  {tp_obj}")
    print(f"False Positives: {fp_obj}")
    print(f"False Negatives: {fn_obj}")
    print(f"Precision: {p_obj}")
    print(f"Recall:    {r_obj}")
    print(f"F1:        {f1_obj}")

    print("\n--- Anomaly Metrics ---")
    print(f"True Positives:  {tp_ano}")
    print(f"False Positives: {fp_ano}")
    print(f"False Negatives: {fn_ano}")
    print(f"Precision: {p_ano}")
    print(f"Recall:    {r_ano}")
    print(f"F1:        {f1_ano}")

    print("\n--- Runtime ---")
    print(f"Avg inference ms/image: {avg_ms}")
    print(f"Approx avg FPS:         {avg_fps}")
    print(f"Wall-clock eval times: {elapsed}")
    print(f"Annotated output directory: {output_dir}")

    if missing_images:
        print("\nMissing/unreadable files (first 20):")
        for name in missing_images[:20]:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
