"""Loose normalized contact-position prior, symmetric under 180-degree rotation.

These configurable image heuristics are not a transcription of ISO dimensions.
Only candidate centers are gated; the metal module need not fit inside a box.
"""

DEFAULT_REGION = [.12, .32, .32, .58]
DEFAULT_MARGIN = [.02, .04]


def expected_regions(cfg: dict) -> list[list[float]]:
    if not cfg.get("position_filter", True):
        return []
    x1,y1,x2,y2 = cfg.get("expected_region",DEFAULT_REGION)
    mx,my = cfg.get("position_margin",DEFAULT_MARGIN)
    first = [max(0.,x1-mx),max(0.,y1-my),min(1.,x2+mx),min(1.,y2+my)]
    return [first,[1-first[2],1-first[3],1-first[0],1-first[1]]]


def position_allowed(box: tuple[int,int,int,int], shape: tuple, cfg: dict) -> bool:
    regions = expected_regions(cfg)
    if not regions:
        return True
    x,y,w,h = box
    cx,cy = (x+w/2)/shape[1],(y+h/2)/shape[0]
    return any(x1-1e-9 <= cx <= x2+1e-9 and y1-1e-9 <= cy <= y2+1e-9 for x1,y1,x2,y2 in regions)
