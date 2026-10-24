"""Retest the same kit with loose, explicitly calibrated search windows.

Calibration is per SOURCE photo, not detector output. The kit's known planar
transforms propagate that window to its variants. No input pixels are modified.
This is an offline ROI experiment, not validation of a physically fixed camera.
"""
from pathlib import Path
import copy
import csv
import json
import math
import sys
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from cardvision.batch import summarize_images
from cardvision.config import load_config
from cardvision.sources import read_image
from cardvision.vision.pipeline import VisionPipeline

OUT=Path(__file__).resolve().parent
KIT=ROOT/'data/test/topdown_kit'
SOURCE=KIT/'images'
OLD=ROOT/'outputs/topdown_kit_baseline/batch_20261024_153642_f36f4efa'
baseline=json.loads((OLD/'results.json').read_text(encoding='utf-8'))
old_rows={row['file']:row for row in baseline['images']}
base_cfg=load_config()
assert base_cfg['input']['rotation']==0 and not base_cfg['input']['mirror']

# Coarse search boxes in source-photo fractions [x,y,width,height]. These are
# deliberately generous, not labelled card corners or chip ground truth.
calibration={
    'aircash_front':[.03,.03,.94,.94], 'aircash_back':[.03,.03,.94,.94],
    'jago_front':[.02,.02,.96,.96], 'jago_back':[.02,.02,.96,.96],
    'nh_front':[.17,.10,.70,.78], 'nh_back':[.13,.08,.72,.80],
    'piraeus_master_front':[.03,.02,.94,.96], 'piraeus_master_back':[.03,.02,.94,.96],
    'piraeus_visa_front':[.03,.03,.94,.94], 'piraeus_visa_back':[.03,.03,.94,.94],
    'plain_back':[.12,.20,.80,.72],
    'sbi_front':[.01,.02,.98,.96], 'sbi_back':[.01,.02,.98,.96],
}
metadata={r['filename'].replace('\\','/').removeprefix('images/'):r for r in csv.DictReader((KIT/'variant_labels.csv').open(encoding='utf-8-sig'))}
assert len(metadata)==156 and all(name in old_rows for name in metadata)


def inspection_window(name: str, shape: tuple) -> list[int]:
    """Map the frozen coarse source window using only kit placement metadata."""
    source_id=Path(name).stem.split('__')[0]
    original=Image.open(SOURCE/'originals'/(source_id+'.jpg'))
    width,height=original.size
    x,y,w,h=calibration[source_id]
    corners=np.array([[x,y],[x+w,y],[x+w,y+h],[x,y+h]],float)*[width,height]
    if name in metadata:
        thumb=original.copy()
        thumb.thumbnail((620,620),Image.Resampling.LANCZOS)
        tw,th=thumb.size
        corners*=np.array([tw/width,th/height])
        entry=metadata[name]
        angle=int(entry['in_plane_rotation_deg'])
        radians=math.radians(angle)
        rotation=np.array([[math.cos(radians),math.sin(radians)],[-math.sin(radians),math.cos(radians)]])
        rw,rh=thumb.rotate(angle,Image.Resampling.BICUBIC,expand=True,fillcolor=(213,213,213)).size
        placement=np.array([(1280-rw)//2+int(entry['x_offset_px']), (960-rh)//2+int(entry['y_offset_px'])])
        corners=(corners-[tw/2,th/2])@rotation.T+[rw/2,rh/2]+placement
        width,height=1280,960
    processed_h=round(shape[0]*base_cfg['input']['width']/shape[1])
    corners*=np.array([base_cfg['input']['width']/width,processed_h/height])
    left,top=np.floor(corners.min(axis=0)).astype(int)
    right,bottom=np.ceil(corners.max(axis=0)).astype(int)
    return [max(0,int(left)),max(0,int(top)),int(right-left),int(bottom-top)]


FONT='C:/Windows/Fonts/malgun.ttf'
font=ImageFont.truetype(FONT,22)
small=ImageFont.truetype(FONT,19)
title_font=ImageFont.truetype(FONT,30)


def draw_prediction(frame: np.ndarray, row: dict) -> Image.Image:
    image=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
    draw=ImageDraw.Draw(image)
    roi=row.get('inspection_roi')
    if roi:
        x,y,w,h=roi
        draw.rectangle((x,y,x+w-1,y+h-1),outline=(50,205,90),width=4)
        draw.text((x+5,y+4),'검사영역',font=font,fill=(20,130,45),stroke_width=1,stroke_fill=(240,255,240))
    for key,color,label in [('card_quad',(0,170,255),'카드'),('chip_polygon',(255,210,0),'IC칩 판정' if row['chip_detected'] else '미확정 후보')]:
        if row.get(key) is None:
            continue
        points=[tuple(float(v) for v in point) for point in row[key]]
        draw.line(points+[points[0]],fill=color,width=4)
        x=min(p[0] for p in points)
        y=max(0,min(p[1] for p in points)-32)
        width=draw.textbbox((0,0),label,font=font)[2]+12
        x=min(x,image.width-width)
        draw.rectangle((x,y,x+width,y+33),fill=color)
        draw.text((x+5,y+1),label,font=font,fill=(10,15,20))
    return image


rows=[]
cfg_rows={}
for old in baseline['images']:
    name=old['file']
    raw=read_image(SOURCE/name)
    cfg=copy.deepcopy(base_cfg)
    cfg['card']['fixed_roi']=inspection_window(name,raw.shape)
    pipeline=VisionPipeline(cfg)
    frame,obs=pipeline.process_image(raw)
    row={'file':name,'group':old['group'],**obs.record(),
         'input_width':raw.shape[1],'input_height':raw.shape[0],
         'processed_width':frame.shape[1],'processed_height':frame.shape[0],
         'nominal_roi':cfg['card']['fixed_roi'],'roi_padding_fraction':cfg['card']['roi_padding_fraction'],
         'error':None,'annotation_error':None,'annotated_path':'annotated/'+name+'.png'}
    destination=OUT/row['annotated_path']
    destination.parent.mkdir(parents=True,exist_ok=True)
    draw_prediction(frame,row).save(destination)
    rows.append(row)
    cfg_rows[name]=cfg['card']['fixed_roi']
summary=summarize_images(rows,{})
summary['card_flags']=sum(r['card_detected'] for r in rows)
summary['chip_flags']=sum(r['chip_detected'] for r in rows)
summary['unknown_count']=sum(r['status']=='UNKNOWN' for r in rows)
summary['changed_results']=[{'file':r['file'],'before':{k:old_rows[r['file']][k] for k in ('card_detected','chip_detected','status','reason')},
                            'after':{k:r[k] for k in ('card_detected','chip_detected','status','reason')}}
                           for r in rows if any(r[k]!=old_rows[r['file']][k] for k in ('card_detected','chip_detected','status','reason'))]
summary['chip_flags_on_back_images']=sum(r['chip_detected'] for r in rows if Path(r['file']).stem.split('__')[0].endswith('back'))
note='Coarse per-source search-window calibration propagated via known kit transforms; extra padding 10% per side. Same image pixels and chip classifier. Not a real fixed-camera trial. Detection flags include wrong boxes; accuracy unlabelled.'
report={'config':base_cfg,'roi_method':note,'source_calibration':calibration,'summary':summary,'images':rows}
(OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'calibrated_windows.json').write_text(json.dumps(cfg_rows,indent=2),encoding='utf-8')
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'results.csv').open('w',encoding='utf-8-sig',newline='') as handle:
    writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,tuple,dict)) else v for k,v in row.items()})

cases=[('aircash_front','실제 칩 검출'),('aircash_back','홀로그램 오검출'),('piraeus_visa_front','결제 아이콘 오검출'),('nh_front','카드 검출 실패')]
sheet=Image.new('RGB',(1400,1910),(245,247,250))
draw=ImageDraw.Draw(sheet)
draw.text((24,14),'같은 이미지 재검사: 여유 있는 검사영역 적용',font=title_font,fill=(20,25,35))
draw.text((24,62),f"169장 | 카드 표시 {summary['card_flags']}장 | 칩 표시 {summary['chip_flags']}장 | UNKNOWN {summary['unknown_count']}장",font=font,fill=(30,40,50))
draw.text((24,100),'초록: 검사영역   파랑: 카드 검출   노랑: 칩 판정/후보 (오검출 포함)',font=font,fill=(30,40,50))
draw.text((24,141),'이전: 전체 화면 검사',font=title_font,fill=(40,45,55))
draw.text((724,141),'이번: 여유 있는 검색창',font=title_font,fill=(40,45,55))
lookup={r['file']:r for r in rows}
for index,(name,title) in enumerate(cases):
    y=200+index*425
    file='originals/'+name+'.jpg'
    draw.text((24,y),name+' — '+title,font=font,fill=(30,35,45))
    raw=read_image(SOURCE/file)
    frame=VisionPipeline(base_cfg).prepare(raw)
    for col,row in enumerate((old_rows[file],lookup[file])):
        image=draw_prediction(frame,row)
        image.thumbnail((650,340),Image.Resampling.LANCZOS)
        x=24+col*700+(650-image.width)//2
        sheet.paste(image,(x,y+38))
        draw.text((24+col*700,y+382),f"{row['status']} / {row['reason']}",font=small,fill=(65,70,80))
sheet.save(OUT/'before_after.png')
print(json.dumps(summary,ensure_ascii=True,indent=2))
