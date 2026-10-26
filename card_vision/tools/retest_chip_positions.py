"""Re-run the supplied top-down kit with the previous, frozen per-image ROIs.

Uses known source side/rotation only for evaluation, never for detection.
The 104-image orientation audit covers the eight unambiguously horizontal
source photos; portrait and oblique sources are still processed and saved.
"""
import argparse
from collections import Counter
import copy
import csv
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cardvision.config import load_config
from cardvision.models import Status
from cardvision.sources import read_image
from cardvision.vision.pipeline import VisionPipeline


def font(size: int):
    for path in ("C:/Windows/Fonts/malgun.ttf","/usr/share/fonts/truetype/nanum/NanumGothic.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path,size)
    return ImageFont.load_default()


def render(frame: np.ndarray, row: dict, threshold: float) -> Image.Image:
    image=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
    draw=ImageDraw.Draw(image)
    for region in row["expected_chip_regions"]:
        points=[tuple(p) for p in region]
        draw.line(points+[points[0]],fill=(195,105,225),width=2)
    if row.get("inspection_roi"):
        x,y,w,h=row["inspection_roi"]
        draw.rectangle((x,y,x+w-1,y+h-1),outline=(50,190,85),width=2)
    if row["card_quad"]:
        points=[tuple(p) for p in row["card_quad"]]
        draw.line(points+[points[0]],fill=(0,165,255),width=3)
    for rejected in row["rejected_chips"]:
        if rejected["score"]<threshold:
            continue
        points=[tuple(p) for p in rejected["polygon"]]
        draw.line(points+[points[0]],fill=(240,55,60),width=3)
        draw.text((max(0,min(p[0] for p in points)),max(0,min(p[1] for p in points)-28)),"위치 제외",font=font(21),fill=(210,20,35),stroke_width=1,stroke_fill=(255,255,255))
    if row["chip_polygon"]:
        points=[tuple(p) for p in row["chip_polygon"]]
        draw.line(points+[points[0]],fill=(255,205,0),width=4 if row["chip_detected"] else 1)
    output=Image.new("RGB",(image.width,image.height+100),(245,247,250))
    output.paste(image,(0,100))
    draw=ImageDraw.Draw(output)
    color=(30,130,60) if row["card_class"].startswith("FRONT") else (30,70,145) if row["card_class"]=="BACK_LIKELY" else (130,95,30)
    draw.text((12,5),row["card_label"],font=font(31),fill=color)
    draw.text((12,48),row["file"],font=font(18),fill=(35,40,45))
    draw.text((12,73),f"{row['status']} / {row['reason']} | {row['processing_ms']:.1f}ms",font=font(17),fill=(55,60,65))
    return output


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images",type=Path,default=ROOT/"data/test/topdown_kit/images")
    parser.add_argument("--previous",type=Path,default=ROOT/"outputs/topdown_roi_retest/results.json")
    parser.add_argument("--output",type=Path,default=ROOT/"outputs/chip_position_retest")
    args=parser.parse_args()
    previous=json.loads(args.previous.read_text(encoding="utf-8"))
    base=load_config()
    args.output.mkdir(parents=True,exist_ok=True)
    old_by_file={r["file"]:r for r in previous["images"]}
    rows=[]
    position_only=[]
    for old in previous["images"]:
        raw=read_image(args.images/old["file"])
        if raw is None:
            raise OSError(f"Cannot read {old['file']}")
        cfg=copy.deepcopy(base)
        cfg["card"]["fixed_roi"]=old["nominal_roi"]
        cfg["card"]["roi_padding_fraction"]=old["roi_padding_fraction"]
        frame,obs=VisionPipeline(cfg).process_image(raw)
        row={"file":old["file"],"group":old["group"],**obs.record(),"error":None,"annotation_error":None,
             "nominal_roi":old["nominal_roi"],"roi_padding_fraction":old["roi_padding_fraction"]}
        path=args.output/"annotated"/(old["file"]+".png")
        path.parent.mkdir(parents=True,exist_ok=True)
        render(frame,row,base["chip"]["min_score"]).save(path)
        rows.append(row)
        cfg["chip"]["edge_candidates"]=False
        _,simple=VisionPipeline(cfg).process_image(raw)
        position_only.append({"file":old["file"],**simple.record()})

    def summary(records):
        classes=Counter(r.get("card_class",{ "CORRECT":"FRONT_CORRECT","REVERSED":"FRONT_REVERSED","CHIP_NOT_VISIBLE":"BACK_LIKELY","UNKNOWN":"UNKNOWN"}[r["status"]]) for r in records)
        back=[r for r in records if Path(r["file"]).stem.split("__")[0].endswith("back")]
        front=[r for r in records if Path(r["file"]).stem.split("__")[0].endswith("front")]
        return {"images":len(records),"classes":dict(classes),"card_flags":sum(r["card_detected"] for r in records),
                "chip_flags":sum(r["chip_detected"] for r in records),"back_images":len(back),
                "chip_flags_on_back":sum(r["chip_detected"] for r in back),
                "back_as_front":sum(r["status"] in ("CORRECT","REVERSED") for r in back),
                "front_as_back":sum(r["status"]=="CHIP_NOT_VISIBLE" for r in front),
                "mean_processing_ms":sum(r["processing_ms"] for r in records)/len(records)}
    results={"previous":summary(previous["images"]),"position_filter_only":summary(position_only),"updated":summary(rows)}
    # Reference labels for the same already-reviewed source images: not a held-out benchmark.
    supported={"aircash_front","aircash_back","nh_front","nh_back","piraeus_visa_front","piraeus_visa_back","sbi_front","sbi_back"}
    labels=[]
    for row in rows:
        stem=Path(row["file"]).stem
        source=stem.split("__")[0]
        if source not in supported:
            continue
        is_front=source.endswith("front")
        rotated="__center_180" in stem or "__up_180" in stem
        truth="CORRECT" if is_front and rotated else "REVERSED" if is_front else "CHIP_NOT_VISIBLE"
        labels.append({"file":row["file"],"card_present":True,"chip_visible":is_front,"status":truth})
    truth_by_file={r["file"]:r["status"] for r in labels}
    audits={}
    for title,records in (("previous",previous["images"]),("updated",rows)):
        audited=[r for r in records if r["file"] in truth_by_file]
        confusion=Counter(f"{truth_by_file[r['file']]} -> {r['status']}" for r in audited)
        audits[title]={"images":len(audited),"correct":sum(r["status"]==truth_by_file[r["file"]] for r in audited),"confusion":dict(confusion)}
    results["horizontal_source_audit"]=audits
    results["note"]="Same development images, same frozen per-image card ROIs; positions are loose heuristic priors, not exact ISO dimensions. Back class is inferred from no valid visible chip. Portrait/oblique sources excluded from the 104-image orientation audit. No chip-box ground truth or unseen-card accuracy claim."
    (args.output/"results.json").write_text(json.dumps({"config":base,"summary":results,"images":rows},ensure_ascii=False,indent=2),encoding="utf-8")
    (args.output/"summary.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    (args.output/"reviewed_horizontal_labels.json").write_text(json.dumps(labels,ensure_ascii=False,indent=2),encoding="utf-8")
    with (args.output/"results.csv").open("w",encoding="utf-8-sig",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,tuple)) else v for k,v in row.items()})

    cases=[("planar_variants/aircash_front__center_180.jpg","앞면 정방향 사례"),
           ("originals/aircash_front.jpg","앞면 반대방향 사례"),
           ("originals/aircash_back.jpg","홀로그램 위치 제외 사례"),
           ("originals/piraeus_visa_front.jpg","실제 칩 / 결제 아이콘 구분"),
           ("planar_variants/piraeus_master_back__center_0.jpg","세로 배치: 기구 방향 판단 보류"),
           ("originals/sbi_back.jpg","남아 있는 오검출 확인")]
    lookup={r["file"]:r for r in rows}
    sheet=Image.new("RGB",(1460,1690),(245,247,250))
    draw=ImageDraw.Draw(sheet)
    draw.text((22,12),"넉넉한 칩 위치 필터 + 앞면 정·역방향 / 뒷면 추정",font=font(31),fill=(20,25,35))
    draw.text((22,61),"보라: 칩 허용 위치   빨강: 위치로 제외   노랑: 남은 칩 후보   파랑: 카드",font=font(23),fill=(40,45,50))
    draw.text((22,103),f"169장 재검사 | 뒷면 칩 검출 표시 {results['previous']['chip_flags_on_back']} → {results['updated']['chip_flags_on_back']} (91장 중)",font=font(24),fill=(25,70,110))
    draw.text((22,146),"미검출은 뒷면 확정이 아닙니다. 세로 배치·화질·검출 실패는 판단 보류할 수 있습니다.",font=font(20),fill=(75,80,90))
    for index,(name,title) in enumerate(cases):
        x=20+(index%2)*730
        y=205+(index//2)*490
        draw.text((x,y),title,font=font(24),fill=(25,30,40))
        image=Image.open(args.output/"annotated"/(name+".png"))
        image.thumbnail((690,410),Image.Resampling.LANCZOS)
        sheet.paste(image,(x+(690-image.width)//2,y+40))
        draw.text((x,y+453),lookup[name]["card_label"]+" / "+lookup[name]["reason"],font=font(18),fill=(65,70,80))
    sheet.save(args.output/"classification_preview.png")
    print(json.dumps(results,ensure_ascii=True,indent=2))


if __name__=="__main__":
    main()
