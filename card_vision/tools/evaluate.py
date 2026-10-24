"""Evaluate metadata logs against manually labelled inclusive frame ranges."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cardvision.models import Status
from cardvision.vision.temporal import Stabilizer


def summarize(rows: list[dict], labels: list[dict], stable_frames: int = 5) -> dict:
    """UNKNOWN counts as a classification result; no labels => no accuracy."""
    timings=[row["processing_ms"] for row in rows]
    report={"processed_frames":len(rows),"mean_processing_ms":statistics.mean(timings) if timings else None,
            "unknown_ratio":sum(r["status"]=="UNKNOWN" for r in rows)/len(rows) if rows else None}
    matched=[]
    confusion=Counter()
    groups=defaultdict(list)
    first_decisions=[]
    for label in labels:
        segment=sorted([r for r in rows if r["file"]==label["file"] and label["start_frame"]<=r["frame"]<=label["end_frame"]],key=lambda r:r["frame"])
        stabilizer=Stabilizer(stable_frames)
        latency=None
        for row in segment:
            matched.append((row,label))
            confusion[(label["status"],row["status"])]+=1
            groups[label.get("card_type","unspecified")].append((row,label))
            stable=stabilizer.update(Status(row["status"]))
            if latency is None and stable!=Status.UNKNOWN and stable.value==label["status"]:
                latency=row["timestamp"]-segment[0]["timestamp"]
        first_decisions.append({"file":label["file"],"start_frame":label["start_frame"],"status":label["status"],
                                "seconds_to_stable_correct":latency})

    def metrics(pairs: list[tuple]) -> dict:
        present=[(r,l) for r,l in pairs if l["card_present"]]
        visible=[(r,l) for r,l in pairs if l["chip_visible"]]
        absent=[(r,l) for r,l in pairs if not l["chip_visible"]]
        return {"labelled_frames":len(pairs),
                "classification_accuracy":sum(r["status"]==l["status"] for r,l in pairs)/len(pairs) if pairs else None,
                "card_detection_recall":sum(r["card_detected"] for r,l in present)/len(present) if present else None,
                "chip_detection_recall":sum(r["chip_detected"] for r,l in visible)/len(visible) if visible else None,
                "chip_false_positive_count":sum(r["chip_detected"] for r,l in absent),
                "card_false_positive_count":sum(r["card_detected"] and not l["card_present"] for r,l in pairs)}
    report.update(metrics(matched))
    report["confusion"]={f"{truth} -> {prediction}":n for (truth,prediction),n in sorted(confusion.items())}
    report["by_card_type"]={key:metrics(value) for key,value in groups.items()}
    report["decision_latency"]=first_decisions
    report["unlabelled_frames"]=len(rows)-len(matched)
    return report


def load_labels(path: Path | None) -> list[dict]:
    if path is None:
        return []
    labels=json.loads(path.read_text(encoding="utf-8"))
    for label in labels:
        Status(label["status"])
        if label["start_frame"]<0 or label["end_frame"]<label["start_frame"]:
            raise ValueError("Invalid label frame interval")
        if not isinstance(label["card_present"],bool) or not isinstance(label["chip_visible"],bool):
            raise ValueError("card_present/chip_visible must be booleans")
    for i,left in enumerate(labels):
        for right in labels[i+1:]:
            if left["file"]==right["file"] and max(left["start_frame"],right["start_frame"])<=min(left["end_frame"],right["end_frame"]):
                raise ValueError("Overlapping labels would double-count frames")
    return labels


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs",nargs="+",required=True,type=Path)
    parser.add_argument("--labels",type=Path)
    parser.add_argument("--stable-frames",type=int,default=5)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.stable_frames<1:
        parser.error("--stable-frames must be positive")
    # Most recent record wins after seeking/replaying or supplying repeated runs.
    unique={}
    for path in args.logs:
        for line in path.read_text(encoding="utf-8").splitlines():
            row=json.loads(line)
            if row.get("kind")=="observation":
                unique[(row["file"],row["frame"])]=row
    result=summarize(list(unique.values()),load_labels(args.labels),args.stable_frames)
    content=json.dumps(result,indent=2,ensure_ascii=False)
    print(content)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(content,encoding="utf-8")
