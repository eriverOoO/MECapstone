"""Reproducible CLI integration and synthetic evaluation, no real card data."""
from pathlib import Path
import json
import subprocess
import sys
import cv2

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generate_demo import generate, synthetic_frame
from evaluate import summarize
from cardvision.config import load_config
from cardvision.control import Controller
from cardvision.sources import write_image
from cardvision.ui import debug_mosaic, overlay
from cardvision.vision.pipeline import VisionPipeline


def verify() -> None:
    output=ROOT/"outputs"/"synthetic_validation"
    output.mkdir(parents=True,exist_ok=True)
    data=ROOT/"data"/"test"
    labels=generate(data)
    rows=[]
    runs=[]
    expected={"correct":"INSERTING","reversed":"ROTATING","back":"FLIPPING",
              "vertical":"ANALYZING","silver":"INSERTING","empty":"WAITING_FOR_CARD"}
    for name,state in expected.items():
        folder=output/name
        result=subprocess.run([sys.executable,str(ROOT/"main.py"),"--source",str(data/f"demo_{name}.avi"),
                               "--headless","--output",str(folder)],capture_output=True,text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)
        log=max((folder/"logs").glob("*.jsonl"),key=lambda p:p.stat().st_mtime_ns)
        events=[json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        end=events[-1]
        assert end["state"]==state,(name,end)
        observations=[r for r in events if r["kind"]=="observation"]
        assert len(observations)==36,(name,len(observations))
        rows.extend(observations)
        runs.append({"case":name,"expected_state":state,"actual_state":end["state"],"frames":36})
    report=summarize(rows,labels)
    report["warning"]="Synthetic fixtures only. Not real-card accuracy or Raspberry Pi throughput."
    report["cli_cases"]=runs
    (output/"evaluation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    cfg=load_config()
    pipeline=VisionPipeline(cfg)
    controller=Controller(cfg["control"],cfg["stability"]["frames"])
    for i in range(6):
        frame,obs=pipeline.process(synthetic_frame("CORRECT"),i,i/15)
        controller.observe(obs)
    write_image(output/"preview.png",overlay(frame,obs,controller,cfg,True,1,1.))
    write_image(output/"intermediates.png",debug_mosaic(obs))
    print(json.dumps({"synthetic_frames":len(rows),"labelled_accuracy":report["classification_accuracy"],
                      "mean_processing_ms":report["mean_processing_ms"],"report":str(output/"evaluation.json")},indent=2))


if __name__=="__main__":
    verify()
