"""Produce local contact sheets and compact diagnostics for the supplied kit."""
import json
from pathlib import Path
import sys
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from cardvision.sources import read_image,write_image

KIT=ROOT/'data/test/topdown_kit'
OUT=Path(__file__).resolve().parent
run=max(OUT.glob('batch_*'),key=lambda p:p.stat().st_mtime_ns)
report=json.loads((run/'results.json').read_text(encoding='utf-8'))
rows={r['file']:r for r in report['images']}
tiles=[]
for path in sorted((KIT/'images/originals').glob('*.jpg')):
    image=read_image(path)
    row=rows['originals/'+path.name]
    h,w=image.shape[:2]
    scale=min(460/w,300/h)
    image=cv2.resize(image,(round(w*scale),round(h*scale)))
    tile=np.full((365,480,3),245,np.uint8)
    tile[35:35+image.shape[0],10:10+image.shape[1]]=image
    cv2.putText(tile,path.stem,(10,24),cv2.FONT_HERSHEY_SIMPLEX,.60,(0,0,0),1)
    cv2.putText(tile,f"card={row['card_detected']} chip={row['chip_detected']} {row['status']}",(10,350),cv2.FONT_HERSHEY_SIMPLEX,.47,(0,0,0),1)
    tiles.append(tile)
for start in range(0,len(tiles),6):
    page=tiles[start:start+6]
    while len(page)<6: page.append(np.full_like(tiles[0],245))
    sheet=np.vstack([np.hstack(page[:2]),np.hstack(page[2:4]),np.hstack(page[4:6])])
    write_image(OUT/f'originals_{start//6+1}.png',sheet)
for row in report['images']:
    print(json.dumps({k:row[k] for k in ('file','card_detected','chip_detected','status','reason','score')},ensure_ascii=True))
