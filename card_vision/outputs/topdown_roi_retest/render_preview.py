"""Render already-saved predictions; no detection or manual box correction."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

OUT=Path(__file__).resolve().parent
report=json.loads((OUT/'results.json').read_text(encoding='utf-8'))
rows={r['file']:r for r in report['images']}
summary=report['summary']
FONT='C:/Windows/Fonts/malgun.ttf'
title=ImageFont.truetype(FONT,31)
font=ImageFont.truetype(FONT,24)
small=ImageFont.truetype(FONT,19)
sheet=Image.new('RGB',(1400,1170),(245,247,250))
draw=ImageDraw.Draw(sheet)
draw.text((24,12),'여유 있는 검사영역으로 재검사한 결과',font=title,fill=(20,25,35))
draw.text((24,61),f"169장 처리 | 카드 표시 {summary['card_flags']}장 | 칩 표시 {summary['chip_flags']}장 | UNKNOWN {summary['unknown_count']}장",font=font,fill=(35,40,50))
for x,color,text in [(24,(50,205,90),'검사영역'),(255,(0,170,255),'카드로 검출'),(525,(255,210,0),'칩 판정/후보 (오검출 포함)')]:
    draw.rectangle((x,112,x+25,136),fill=color)
    draw.text((x+37,106),text,font=font,fill=(30,35,45))
draw.text((24,151),'원본별로 넉넉한 검색창 설정 + 각 방향 10% 여유. 칩 분류 알고리즘은 이전과 동일.',font=small,fill=(75,80,90))
cases=[('planar_variants/aircash_front__left_12.jpg','이동·회전한 카드: 실제 칩 검출'),
       ('originals/aircash_back.jpg','홀로그램을 칩으로 오검출: 여전히 남음'),
       ('originals/piraeus_visa_front.jpg','결제 아이콘을 칩으로 오검출: 여전히 남음'),
       ('planar_variants/plain_back__center_0.jpg','사진 배경 오검출 제외: 실제 카드는 미검출')]
for index,(name,text) in enumerate(cases):
    x=20+(index%2)*700
    y=205+(index//2)*475
    draw.text((x,y),text,font=font,fill=(25,30,40))
    image=Image.open(OUT/'annotated'/(name+'.png'))
    image.thumbnail((660,380),Image.Resampling.LANCZOS)
    sheet.paste(image,(x+(660-image.width)//2,y+45))
    draw.text((x,y+430),f"{rows[name]['status']} / {rows[name]['reason']}",font=small,fill=(65,70,80))
sheet.save(OUT/'roi_results_preview.png')
print(OUT/'roi_results_preview.png')
