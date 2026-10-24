"""OpenCV desktop view. All redraws are separate from new observations."""
import cv2
import numpy as np
from .models import Action, Observation, Status
from .vision.geometry import INLET, project

WINDOW = "Card IC Vision - simulation only"


def suggested_action(status: Status) -> str:
    """A still-image suggestion, never an actuator command."""
    return {Status.CORRECT:Action.INSERT, Status.REVERSED:Action.ROTATE_180,
            Status.CHIP_NOT_VISIBLE:Action.FLIP, Status.UNKNOWN:Action.RECHECK}[status].value


def overlay(frame: np.ndarray, obs: Observation, controller, cfg: dict, paused: bool, stride: int, speed: float, *, still_image: bool = False) -> np.ndarray:
    view = frame.copy()
    if obs.inspection_roi is not None:
        x,y,w,h=obs.inspection_roi
        cv2.rectangle(view,(x,y),(x+w-1,y+h-1),(80,180,80),1)
        cv2.putText(view,"SEARCH ROI",(x+5,y+18),cv2.FONT_HERSHEY_SIMPLEX,.5,(80,180,80),1)
    if obs.card_quad is not None:
        cv2.polylines(view,[obs.card_quad.astype(np.int32)],True,(255,170,0),2)
    if obs.chip_polygon is not None:
        cv2.polylines(view,[obs.chip_polygon.astype(np.int32)],True,(0,220,255),2)
    if obs.chip_center:
        center = tuple(round(v) for v in obs.chip_center)
        cv2.circle(view,center,5,(0,0,255),-1)
        cv2.putText(view,f"{center}",(center[0]+5,center[1]-8),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,0,255),1)
    h,w = frame.shape[:2]
    origin = np.array([[w*.78,h*.90]])
    try:
        stage = project(origin,np.asarray(cfg["orientation"]["image_to_stage"]))
        # Inverse-map a stage-space direction, including camera mirroring/calibration.
        inverse = np.linalg.inv(np.asarray(cfg["orientation"]["image_to_stage"],dtype=float))
        delta = project(stage+np.array(INLET[cfg["orientation"]["inlet"]])*50,inverse)[0]-origin[0]
        delta = delta / max(1e-6,np.linalg.norm(delta))*65
        cv2.arrowedLine(view,tuple(origin[0].astype(int)),tuple((origin[0]+delta).astype(int)),(180,0,255),3)
        cv2.putText(view,"INLET",(int(w*.73),int(h*.90)-15),cv2.FONT_HERSHEY_SIMPLEX,.55,(180,0,255),2)
    except (ValueError,np.linalg.LinAlgError):
        pass
    panel = np.full((260,w,3),25,np.uint8)
    rows = [f"Frame {obs.frame}  t={obs.timestamp:.2f}s   {'PAUSED' if paused else 'PLAY'}   stride={stride} speed={speed:.2f}x",
            f"Frame: {obs.status.value}   stable: {controller.stable.value if not still_image else 'N/A'}",
            f"State: {controller.state if not still_image else 'IMAGE_REVIEW'}   next action: {controller.next_action if not still_image else 'NONE'}",
            f"Chip: {obs.chip_detected}   heuristic score: {obs.score:.2f} (NOT probability)",
            f"Reason: {obs.reason} / {controller.reason if not still_image else 'review_only'}",
            f"Processing: {obs.processing_ms:.1f} ms   compute FPS: {1000/max(.001,obs.processing_ms):.1f}",
            "space play | n/right next | b/left back | +/- speed | [ ] stride | d debug",
            "a ACK success | x ACK failure | r reset cycle | o open file | s save | q quit"]
    if still_image:
        rows[0] = "SINGLE IMAGE REVIEW | motion / temporal stability: N/A"
        rows[1] = f"Image: {obs.status.value}   Card: {obs.card_detected}   Chip: {obs.chip_detected}"
        rows[2] = f"Suggested action: {suggested_action(obs.status)} (review only)"
        rows[4] = f"Reason: {obs.reason}"
        rows[6] = "d intermediates | o open another file | s save annotated image + JSON"
        rows[7] = "q / Esc quit | no actuator commands in image mode"
    for row,text in enumerate(rows):
        cv2.putText(panel,text,(12,25+row*30),cv2.FONT_HERSHEY_SIMPLEX,.49,(225,225,225),1,cv2.LINE_AA)
    return np.vstack((view,panel))


def debug_mosaic(obs: Observation) -> np.ndarray:
    tiles=[]
    for key,value in obs.debug.items():
        if not isinstance(value,np.ndarray):
            continue
        if value.ndim == 2:
            value=cv2.cvtColor(value,cv2.COLOR_GRAY2BGR)
        tile=cv2.resize(value,(320,200))
        cv2.rectangle(tile,(0,0),(320,25),(0,0,0),-1)
        cv2.putText(tile,key,(8,18),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
        tiles.append(tile)
    while len(tiles)%3:
        tiles.append(np.zeros((200,320,3),np.uint8))
    return np.vstack([np.hstack(tiles[i:i+3]) for i in range(0,len(tiles),3)])


def choose_file(initial: str) -> str:
    """Use the standard OS chooser only; tkinter is optional on Linux."""
    try:
        import tkinter as tk
        from tkinter.filedialog import askopenfilename
        root=tk.Tk()
        root.withdraw()
        try:
            return askopenfilename(initialdir=initial,filetypes=[("Images","*.jpg *.JPG *.jpeg *.JPEG *.png *.PNG *.bmp *.BMP *.webp *.WEBP"),("Videos","*.mov *.MOV *.mp4 *.MP4 *.avi"),("All files","*.*")])
        finally:
            root.destroy()
    except ImportError as error:
        raise RuntimeError("File chooser needs tkinter; use --source instead (Linux: python3-tk)") from error
