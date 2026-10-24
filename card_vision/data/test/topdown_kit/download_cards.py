#!/usr/bin/env python3
"""Download freely licensed single-card overhead/scan images, create ONLY 2D planar variants.
Use python download_cards.py, or python download_cards.py --augment-only after placing manual files.
Input JPG/PNG files named <id>.jpg in originals/ for any failed downloads.
"""
import argparse
import csv
import io
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent
ORIG = ROOT / 'images' / 'originals'
VAR = ROOT / 'images' / 'planar_variants'
USER_AGENT = 'CardVisionEducationalTopDownDataset/1.1 (study; contact: card-vision-research@example.org)'
MAX_DIM = 1300


def fetch_file(name: str, session: requests.Session):
    params = {'action': 'query', 'format': 'json', 'prop': 'imageinfo',
              'iiprop': 'url', 'iiurlwidth': str(MAX_DIM), 'titles': 'File:' + name}
    r = session.get('https://commons.wikimedia.org/w/api.php', params=params, timeout=35)
    r.raise_for_status()
    payload = r.json()
    page = next(iter(payload['query']['pages'].values()))
    if not page.get('imageinfo'):
        raise RuntimeError(f'Image not found on Commons: {name}')
    info = page['imageinfo'][0]
    url = info.get('thumburl', info['url'])
    r = session.get(url, timeout=70)
    r.raise_for_status()
    return r.content, url


def image_from_bytes(content: bytes) -> Image.Image:
    with Image.open(io.BytesIO(content)) as im:
        im = ImageOps.exif_transpose(im).convert('RGB')
    im.thumbnail((MAX_DIM, MAX_DIM), Image.Resampling.LANCZOS)
    return im


def compose_planar(img: Image.Image, angle: int, dx: int, dy: int,
                   canvas_size=(1280, 960), quality='default') -> Image.Image:
    # 2D rotation is IN THE CARD PLANE. The camera never tilts.
    img = img.copy()
    img.thumbnail((620, 620), Image.Resampling.LANCZOS)
    if quality == 'dim':
        img = ImageEnhance.Brightness(img).enhance(.50)
    elif quality == 'soft_blur':
        img = img.filter(ImageFilter.GaussianBlur(2.2))
    elif quality == 'lowres':
        s = (max(2, img.width//5), max(2, img.height//5))
        img = img.resize(s, Image.Resampling.BILINEAR).resize(img.size, Image.Resampling.BILINEAR)
    rotated = img.rotate(angle, Image.Resampling.BICUBIC, expand=True, fillcolor=(213, 213, 213))
    board = Image.new('RGB', canvas_size, (213, 213, 213))
    x = (board.width - rotated.width)//2 + dx
    y = (board.height - rotated.height)//2 + dy
    board.paste(rotated, (x, y))
    return board


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--augment-only', action='store_true', help='Skip download; process manually saved images')
    args = ap.parse_args()
    ORIG.mkdir(parents=True, exist_ok=True)
    VAR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((ROOT / 'sources.csv').open(encoding='utf-8-sig')))
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    fetch_results = []
    labels = []
    # [name, planar angle in degrees, horizontal offset, vertical offset, degradation]
    transforms = [
        ('center_0',0,0,0,'default'), ('center_180',180,0,0,'default'),
        ('left_0',0,-190,0,'default'), ('right_0',0,190,0,'default'),
        ('up_0',0,0,-130,'default'), ('down_0',0,0,130,'default'),
        ('left_12',12,-150,0,'default'), ('right_m12',-12,150,0,'default'),
        ('up_180',180,0,-110,'default'), ('dim_0',0,0,0,'dim'),
        ('blur_0',0,0,0,'soft_blur'), ('lowres_0',0,0,0,'lowres'),
    ]
    for row in rows:
        candidate = list(ORIG.glob(row['id'] + '.*'))
        source_url = ''
        try:
            if candidate:
                input_path = candidate[0]
                with Image.open(input_path) as im:
                    img = ImageOps.exif_transpose(im).convert('RGB')
            elif args.augment_only:
                raise FileNotFoundError('Image not present in originals/')
            else:
                content, source_url = fetch_file(row['commons_filename'], session)
                img = image_from_bytes(content)
                input_path = ORIG / (row['id'] + '.jpg')
                img.save(input_path, quality=92)
                time.sleep(.4)
            fetch_results.append({'id':row['id'],'ok':True,'file':str(input_path.relative_to(ROOT)), 'download_url':source_url})
            print('OK', row['id'])
            for suffix,ang,dx,dy,quality in transforms:
                fname = f'{row["id"]}__{suffix}.jpg'
                dest = VAR / fname
                compose_planar(img, ang, dx, dy, quality=quality).save(dest, quality=90)
                labels.append({'filename':str(dest.relative_to(ROOT)), 'source_id':row['id'],
                               'card_side':row['side'], 'chip_expected': 'yes' if row['side']=='front' else 'no',
                               'in_plane_rotation_deg':ang, 'x_offset_px':dx, 'y_offset_px':dy,
                               'image_effect':quality,
                               'orientation_action_label':'not_labeled_without_insert_direction'})
        except Exception as exc:
            print(f'FAILED {row["id"]}: {exc}', file=sys.stderr)
            fetch_results.append({'id':row['id'],'ok':False,'error':str(exc),'source':row['source_url']})
    with (ROOT/'variant_labels.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields = ['filename','source_id','card_side','chip_expected','in_plane_rotation_deg','x_offset_px','y_offset_px','image_effect','orientation_action_label']
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(labels)
    (ROOT/'download_results.json').write_text(json.dumps(fetch_results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'\nSources: {sum(x["ok"] for x in fetch_results)}/{len(rows)}; test images: {len(labels)}')
    print('IMPORTANT: These images are not independent real-world photos; see README.')

if __name__ == '__main__':
    main()
