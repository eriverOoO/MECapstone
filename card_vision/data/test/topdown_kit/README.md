# Single-card top-down IC-chip vision evaluation kit

## Assumptions (real apparatus)
- Fixed camera perpendicular to flat card stage (top-down only)
- ONE card in each frame
- Card may be shifted relative to camera center
- Card may rotate **in its own plane** (0°, 180°, small planar yaw)
- **No tilted camera perspective** and no multiple cards, hands, laptops, extreme closeups

## Sources
`./sources.csv` lists 13 Wikimedia Commons **front/back photo or flat scan source files**.
- Smartphone/direct-overhead photographs: NH pair, Bank Jago pair, SBI pair, blank back
- Plane scans: Piraeus Mastercard pair, Piraeus Visa pair, Aircash pair
- Scans are valuable for orientation baselines but are not realistic camera images.
- Photographer, licenses and attribution URLs preserved in `sources.csv`.
- Original source content was not embedded in this ZIP (execution environment couldn't access the image host).
- Source-view angle and chip visibility should be checked after downloads; the above grouping is based on file descriptions and media type, not pixel-level visual QC.

## Run on an internet-connected PC
```bash
python -m pip install requests Pillow
python download_cards.py
```

Outputs:
- `images/originals/` actual downloaded pictures/scans
- `images/planar_variants/` planar 2D rotated/translated/dim/blur/low-resolution variants (up to 12 per source)
- `variant_labels.csv` records side, rotations, translations, and image effects
- `download_results.json` records failures (and successful source URL)

If Wikimedia Commons API or thumbnail access is blocked/rate-limited, manually download desired pictures from the `source_url` column into `images/originals/` as `<id>.jpg` or `<id>.png` and run:
```bash
python download_cards.py --augment-only
```

## Important limits
- These shifted/rotated images are **synthetic transformations of real front/back images**, not separate real camera photographs.
- Shifting the cropped source image also shifts its original photographic background; for fully realistic backgrounds, use actual iPhone video on the stage.
- This set only tests initial chip/no-chip recognition and stability when translated or rotated in-plane.
- The script **does not declare CORRECT/REVERSED**, because machine insertion direction must be defined in stage coordinates first.
- A missed chip is not sufficient proof of reverse side: use confidence/recheck/UNKNOWN safeguards.
- Some cards differ in chip side and design. Verify source images before treating automatic `chip_expected` labels as truth.
- Do not use any real unredacted card details in screenshots or public repos.
- The licenses in sources.csv may carry attribution/share-alike requirements. Check each file description prior to redistribution or publishing derived photos.
