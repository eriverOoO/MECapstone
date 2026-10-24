"""Draw saved baseline detector regions directly on each processed source image."""
from pathlib import Path
import json
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cardvision.sources import read_image, write_image
from cardvision.vision.pipeline import VisionPipeline

BASE = Path(__file__).resolve().parent
RUN = BASE/'batch_20261024_153642_f36f4efa'
report = json.loads((RUN/'results.json').read_text(encoding='utf-8'))
pipeline = VisionPipeline(report['config'])
SOURCE = ROOT/'data/test/topdown_kit/images'
OUT = BASE/'region_overlays'
FONT = 'C:/Windows/Fonts/malgun.ttf'
font = ImageFont.truetype(FONT, 22)
titlefont = ImageFont.truetype(FONT, 25)
small = ImageFont.truetype(FONT, 19)


def label(draw, text, x, y, color):
    bounds=draw.textbbox((0,0),text,font=font)
    width,height=bounds[2]-bounds[0]+16,34
    x=max(0,min(int(x),draw._image.width-width))
    y=max(0,min(int(y),draw._image.height-height))
    draw.rectangle((x,y,x+width,y+height),fill=color)
    draw.text((x+8,y+2),text,font=font,fill=(12,12,12))


for row in report['images']:
    raw=read_image(SOURCE/row['file'])
    if raw is None:
        continue
    frame=pipeline.prepare(raw)
    # Coordinates are those already recorded by the detector, with no manual corrections.
    for field,color in [('card_quad',(255,170,0)),('chip_polygon',(0,220,255))]:
        if row[field] is None:
            continue
        points=np.asarray(row[field],np.int32)
        tint=frame.copy()
        cv2.fillPoly(tint,[points],color)
        frame=cv2.addWeighted(tint,.14,frame,.86,0)
        cv2.polylines(frame,[points],True,color,4)
    image=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
    draw=ImageDraw.Draw(image)
    if row['card_quad'] is not None:
        points=np.asarray(row['card_quad'])
        label(draw,'카드로 검출',points[:,0].min(),points[:,1].min()-35,(0,170,255))
    if row['chip_polygon'] is not None:
        points=np.asarray(row['chip_polygon'])
        label(draw,'IC칩으로 판정' if row['chip_detected'] else '칩 후보 (미확정)',
              points[:,0].min(),points[:,1].min()-35,(255,220,0))
    destination=OUT/(row['file']+'.png')
    destination.parent.mkdir(parents=True,exist_ok=True)
    image.save(destination)

cases=[('aircash_front','실제 칩을 검출한 사례'),
       ('aircash_back','오검출: 뒷면 홀로그램을 칩으로 판단'),
       ('piraeus_visa_front','오검출: 결제 아이콘을 칩으로 판단'),
       ('nh_front','카드 외곽 검출 실패: 표시할 영역 없음')]
sheet=Image.new('RGB',(1400,1110),(245,247,250))
draw=ImageDraw.Draw(sheet)
draw.text((24,12),'실제 검출 결과를 원본 위에 표시',font=ImageFont.truetype(FONT,32),fill=(20,25,35))
draw.rectangle((24,68,49,90),fill=(0,170,255))
draw.text((60,62),'카드로 검출',font=font,fill=(25,30,40))
draw.rectangle((270,68,295,90),fill=(255,220,0))
draw.text((306,62),'IC칩으로 판정 (오검출 포함)',font=font,fill=(25,30,40))
draw.text((24,103),'표시한 영역은 프로그램의 예측이며, 정답을 수동으로 그린 것이 아닙니다.',font=small,fill=(65,70,80))
for index,(name,title) in enumerate(cases):
    x=20+(index%2)*700
    y=155+(index//2)*475
    draw.text((x,y),title,font=titlefont,fill=(25,30,40))
    image=Image.open(OUT/'originals'/(name+'.jpg.png'))
    image.thumbnail((660,390),Image.Resampling.LANCZOS)
    sheet.paste(image,(x+(660-image.width)//2,y+45))
    draw.text((x,y+440),name+'.jpg',font=small,fill=(85,90,100))
sheet.save(BASE/'detection_regions_preview.png')
print(f'Saved {len(report["images"])} region overlays and detection_regions_preview.png')
