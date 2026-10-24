from datetime import datetime
from pathlib import Path
import json
import uuid
from .models import Observation
from .sources import write_image


class RunLogger:
    def __init__(self, directory: Path, source: str):
        self.directory = directory
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
        (directory/"logs").mkdir(parents=True,exist_ok=True)
        self.path = directory/"logs"/(self.run_id+".jsonl")
        self.handle = self.path.open("w",encoding="utf-8")
        self.source = Path(source).name

    def event(self, kind: str, **values) -> None:
        self.handle.write(json.dumps({"kind":kind,"file":self.source,**values},ensure_ascii=False,allow_nan=False)+"\n")
        self.handle.flush()

    def observation(self, obs: Observation, controller, *, still_image: bool = False) -> None:
        self.event("observation", **obs.record(),stable_status=controller.stable.value,
                   input_mode="image" if still_image else "video",
                   controller_state="IMAGE_REVIEW" if still_image else controller.state,
                   next_action="NONE" if still_image else controller.next_action,
                   controller_reason="review_only" if still_image else controller.reason)

    def snapshot(self, frame, obs: Observation) -> Path:
        folder = self.directory/"frames"/self.run_id
        folder.mkdir(parents=True,exist_ok=True)
        path = folder/f"frame_{obs.frame:08d}.png"
        write_image(path,frame)
        path.with_suffix(".json").write_text(json.dumps(obs.record(),ensure_ascii=False,indent=2),encoding="utf-8")
        return path

    def close(self) -> None:
        self.handle.close()
