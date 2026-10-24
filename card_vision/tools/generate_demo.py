"""Generate fictional cards, videos and frame-range ground truth locally."""
from pathlib import Path
import argparse
import json
import sys
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cardvision.sources import write_image


def synthetic_frame(status: str, angle: float = 0, silver: bool = False, offset: int = 0) -> np.ndarray:
    """Plain synthetic geometry tests only, not a model of real card diversity."""
    card=np.full((300,476,3),(155,90,45),np.uint8)
    cv2.rectangle(card,(2,2),(473,297),(225,225,225),3)
    cv2.putText(card,"SYNTHETIC DEMO",(100,50),cv2.FONT_HERSHEY_SIMPLEX,.7,(240,240,240),2)
    cv2.putText(card,"NO PERSONAL DATA",(110,265),cv2.FONT_HERSHEY_SIMPLEX,.55,(220,220,220),1)
    # Decoration on reverse side gives the quality gate actual texture.
    for y in (100,120,140):
        cv2.line(card,(150,y),(320,y),(195,150,100),2)
    if status in ("CORRECT","REVERSED"):
        x=350 if status=="CORRECT" else 65
        color=(185,185,185) if silver else (45,175,215)
        cv2.rectangle(card,(x,105),(x+60,177),color,-1)
        cv2.rectangle(card,(x,105),(x+60,177),(30,45,50),2)
        for y in (128,153):
            cv2.line(card,(x+2,y),(x+58,y),(35,40,45),2)
        for dx in (20,40):
            cv2.line(card,(x+dx,107),(x+dx,175),(35,40,45),2)
    canvas=np.full((540,960,3),32,np.uint8)
    source=np.array([[0,0],[475,0],[475,299],[0,299]],np.float32)
    corners=np.array([[-238,-150],[238,-150],[238,150],[-238,150]],np.float32)
    radians=np.radians(angle)
    rotation=np.array([[np.cos(radians),-np.sin(radians)],[np.sin(radians),np.cos(radians)]])
    destination=(corners@rotation.T+np.array([480+offset,270])).astype(np.float32)
    matrix=cv2.getPerspectiveTransform(source,destination)
    warped=cv2.warpPerspective(card,matrix,(960,540))
    mask=cv2.warpPerspective(np.full((300,476),255,np.uint8),matrix,(960,540))
    canvas[mask>0]=warped[mask>0]
    if status=="NO_CARD":
        canvas[:]=32
    return canvas


def generate(directory: Path, frames: int = 36) -> list[dict]:
    directory.mkdir(parents=True,exist_ok=True)
    labels=[]
    cases=[("correct","CORRECT",0,False),("reversed","REVERSED",0,False),
           ("back","CHIP_NOT_VISIBLE",0,False),("vertical","CORRECT",90,False),
           ("silver","CORRECT",0,True),("empty","NO_CARD",0,False)]
    for name,status,angle,silver in cases:
        path=directory/f"demo_{name}.avi"
        writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"MJPG"),15,(960,540))
        if not writer.isOpened():
            raise OSError("MJPG video writer is unavailable")
        try:
            for _ in range(frames):
                writer.write(synthetic_frame(status,angle,silver))
        finally:
            writer.release()
        write_image(directory/f"demo_{name}.png",synthetic_frame(status,angle,silver))
        labels.append({"file":path.name,"start_frame":0,"end_frame":frames-1,
                       "card_type":"synthetic_silver" if silver else "synthetic_blue",
                       "card_present":status!="NO_CARD", "chip_visible":status in ("CORRECT","REVERSED"),
                       "status":"UNKNOWN" if angle==90 or status=="NO_CARD" else status})
    (directory/"labels.json").write_text(json.dumps(labels,indent=2),encoding="utf-8")
    return labels


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory",type=Path,default=ROOT/"data"/"test")
    parser.add_argument("--frames",type=int,default=36)
    args=parser.parse_args()
    if args.frames<1:
        parser.error("--frames must be positive")
    generate(args.directory,args.frames)
    print(f"Wrote synthetic fixtures and labels to {args.directory}")
