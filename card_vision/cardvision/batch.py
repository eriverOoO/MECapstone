"""Independent image testing with reproducible metadata and optional overlays."""
import csv
from datetime import datetime
import json
from pathlib import Path
import statistics
import time
import uuid
import cv2
from .models import Status
from .sources import IMAGE_EXTENSIONS, read_image, write_image
from .ui import overlay, suggested_action
from .vision.pipeline import VisionPipeline


def load_image_labels(path: Path | None) -> dict[str, dict]:
    """Optional exact per-image truth, keyed by input-relative POSIX filename."""
    if path is None:
        return {}
    labels = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(labels, list):
        raise ValueError("Image labels must be a JSON list")
    indexed = {}
    for label in labels:
        if not isinstance(label,dict) or not {"file","status","card_present","chip_visible"} <= label.keys():
            raise ValueError("Each image label needs file, status, card_present and chip_visible")
        if not isinstance(label["file"],str):
            raise ValueError("Image label file must be a relative filename string")
        name = label["file"].replace("\\", "/")
        if name in indexed:
            raise ValueError(f"Duplicate image label: {name}")
        Status(label["status"])
        if any(not isinstance(label[k], bool) for k in ("card_present", "chip_visible")):
            raise ValueError("card_present and chip_visible labels must be booleans")
        indexed[name] = label
    return indexed


def summarize_images(rows: list[dict], labels: dict[str, dict]) -> dict:
    """Detection rates describe outputs; only labelled data yields accuracy."""
    decoded = [row for row in rows if row["error"] is None]
    pairs = [(row, labels[row["file"]]) for row in decoded if row["file"] in labels]
    visible = [(r,l) for r,l in pairs if l["chip_visible"]]
    present = [(r,l) for r,l in pairs if l["card_present"]]
    confusion = {}
    for row,label in pairs:
        key = f"{label['status']} -> {row['status']}"
        confusion[key] = confusion.get(key,0)+1
    return {"total_images":len(rows), "processed_images":len(decoded), "read_or_processing_errors":len(rows)-len(decoded),
            "annotation_errors":sum(row["annotation_error"] is not None for row in rows),
            "card_detection_rate":sum(r["card_detected"] for r in decoded)/len(decoded) if decoded else None,
            "chip_detection_rate":sum(r["chip_detected"] for r in decoded)/len(decoded) if decoded else None,
            "unknown_ratio":sum(r["status"]=="UNKNOWN" for r in decoded)/len(decoded) if decoded else None,
            "mean_processing_ms":statistics.mean(r["processing_ms"] for r in decoded) if decoded else None,
            "labelled_images":len(pairs),
            "labelled_input_errors":sum(row["error"] is not None and row["file"] in labels for row in rows),
            "classification_accuracy":sum(r["status"]==l["status"] for r,l in pairs)/len(pairs) if pairs else None,
            "card_detection_recall":sum(r["card_detected"] for r,l in present)/len(present) if present else None,
            "chip_detection_recall":sum(r["chip_detected"] for r,l in visible)/len(visible) if visible else None,
            "card_false_positive_count":sum(r["card_detected"] and not l["card_present"] for r,l in pairs) if pairs else None,
            "chip_false_positive_count":sum(r["chip_detected"] and not l["chip_visible"] for r,l in pairs) if pairs else None,
            "confusion":confusion}


def run_batch(folder: str | Path, output: str | Path, cfg: dict, *, recursive: bool = False,
              save_annotated: bool = False, labels_path: str | Path | None = None) -> Path:
    """Process every supported file once, continuing after individual bad files."""
    root, base = Path(folder).resolve(), Path(output).resolve()
    if not root.is_dir():
        raise ValueError(f"Batch input is not a directory: {folder}")
    if base == root:
        raise ValueError("Batch output must differ from the input directory")
    labels = load_image_labels(Path(labels_path) if labels_path else None)
    iterator = root.rglob("*") if recursive else root.iterdir()
    files = sorted((p for p in iterator if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
                    and not (base.is_relative_to(root) and p.resolve().is_relative_to(base))),
                   key=lambda p:p.relative_to(root).as_posix().casefold())
    if not files:
        raise ValueError(f"No supported images in {folder}")
    run = base/("batch_"+datetime.now().strftime("%Y%m%d_%H%M%S")+"_"+uuid.uuid4().hex[:8])
    run.mkdir(parents=True,exist_ok=False)
    pipeline = VisionPipeline(cfg)
    rows = []
    for path in files:
        started = time.perf_counter()
        relative = path.relative_to(root)
        row = {"file":relative.as_posix(), "group":relative.parts[0] if len(relative.parts)>1 else "(root)",
               "input_width":None, "input_height":None, "processed_width":None, "processed_height":None,
               "card_detected":None, "chip_detected":None, "card_quad":None, "card_box":None, "inspection_roi":None,
               "chip_box":None, "chip_polygon":None, "chip_image_box":None, "chip_center":None, "chip_relative":None,
               "status":"UNKNOWN", "suggested_action":"RECHECK", "score":None, "card_score":None,
               "reason":"decode_failed", "processing_ms":None, "total_ms":None,
               "annotated_path":None, "error":None, "annotation_error":None}
        try:
            raw = read_image(path)
            if raw is None:
                raise OSError("Image decoder returned no pixels")
            row["input_height"],row["input_width"] = raw.shape[:2]
            frame,obs = pipeline.process_image(raw)
            row.update(obs.record())
            row["processed_height"],row["processed_width"] = frame.shape[:2]
            row["suggested_action"] = suggested_action(obs.status)
            if obs.card_quad is not None:
                row["card_box"] = list(cv2.boundingRect(obs.card_quad.astype("float32")))
            if obs.chip_polygon is not None:
                row["chip_image_box"] = list(cv2.boundingRect(obs.chip_polygon.astype("float32")))
        except (OSError, ValueError, cv2.error) as error:
            row["error"] = f"{type(error).__name__}: {error}"
            if row["input_width"] is not None:
                row["reason"] = "processing_error"
        else:
            if save_annotated:
                try:
                    # Include the original suffix: same-stem JPG/PNG never overwrite.
                    destination = run/"annotated"/relative.parent/(relative.name+".png")
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    write_image(destination,overlay(frame,obs,None,cfg,True,1,1.,still_image=True))
                    row["annotated_path"] = destination.relative_to(run).as_posix()
                except (OSError, cv2.error) as error:
                    row["annotation_error"] = f"{type(error).__name__}: {error}"
        row["total_ms"] = (time.perf_counter()-started)*1000
        rows.append(row)
    summary = summarize_images(rows,labels)
    groups = sorted({row["group"] for row in rows})
    summary["by_group"] = {group:summarize_images([r for r in rows if r["group"]==group],labels) for group in groups}
    summary["unmatched_labels"] = sorted(set(labels)-{row["file"] for row in rows})
    summary["note"] = "Unlabelled detection rates are not accuracy. Still images do not provide temporal stability or motion evidence."
    report = {"mode":"batch_images", "config":cfg,
              "coordinates":{"card_quad/card_box/chip_polygon/chip_image_box/chip_center":"processed image pixels before the UI panel",
                             "chip_box":"normalized card pixels; may be a weak candidate when chip_detected=false",
                             "chip_relative":"normalized card coordinates in [0,1]"},
              "summary":summary, "images":rows}
    (run/"results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (run/"results.csv").open("w",encoding="utf-8-sig",newline="") as handle:
        writer = csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,tuple,dict)) else v for k,v in row.items()})
    (run/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    return run
