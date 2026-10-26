"""Heuristic gold/silver chip candidates; scores are not probabilities."""
from dataclasses import dataclass
import cv2
import numpy as np
from .chip_position import expected_regions, position_allowed
from .chip_geometry import oversized_and_wide


@dataclass
class ChipCandidate:
    box: tuple[int, int, int, int]
    score: float
    method: str = "color"


class ChipDetector:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def detect(self, card: np.ndarray) -> tuple[list[ChipCandidate], dict]:
        hsv = cv2.cvtColor(card, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(card, cv2.COLOR_BGR2GRAY)
        gold = cv2.inRange(hsv, np.array(self.cfg["hsv_lower"]), np.array(self.cfg["hsv_upper"]))
        # Silver branch uses bright low-saturation regions; geometry + contact
        # pattern checks must reject blank panels. Neither branch proves metal.
        silver = cv2.inRange(hsv, np.array([0,0,95]), np.array([179,65,245]))
        candidates = []
        debug = {"gold_mask": gold, "silver_mask": silver}
        preview = card.copy()
        h,w = gray.shape
        branches=[(gold,1.,"gold"),(silver,.7,"silver")]
        if self.cfg.get("edge_candidates",True):
            borders=cv2.Canny(cv2.GaussianBlur(gray,(3,3),0),40,110)
            debug["chip_edges"]=borders
            branches.append((borders,.6,"edge"))
        rejected=[]
        for mask, metallic_bonus, method in branches:
            joined = mask if method=="edge" else cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))
            contours, _ = cv2.findContours(joined, cv2.RETR_LIST if method=="edge" else cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x,y,bw,bh = cv2.boundingRect(contour)
                fraction = bw*bh/(w*h)
                if not self.cfg["min_area_fraction"] < fraction < self.cfg["max_area_fraction"]:
                    continue
                aspect = bw/max(1,bh)
                if not .60 < aspect < 1.85 or x < 5 or y < 5 or x+bw > w-5 or y+bh > h-5:
                    continue
                fill = cv2.contourArea(contour)/(bw*bh)
                if fill < (.70 if method=="edge" else .6):
                    continue
                patch = gray[y:y+bh, x:x+bw]
                inner = patch[max(2,bh//8):bh-max(2,bh//8), max(2,bw//8):bw-max(2,bw//8)]
                if inner.size < 20:
                    continue
                # Interior contact seams: uniform gold logos do not earn a high score.
                seam_edges = cv2.Canny(inner, 35, 100)
                density = np.count_nonzero(seam_edges)/inner.size
                texture = min(1., density/.10) if density < .35 else .15
                lines = cv2.HoughLinesP(seam_edges, 1, np.pi/180, threshold=max(6,min(bw,bh)//5),
                                        minLineLength=max(5,min(bw,bh)//4), maxLineGap=3)
                line_count = 0 if lines is None else len(lines)
                pattern = min(1., line_count/4)
                score = float(.15*metallic_bonus + .20*min(1.,fill) + .30*texture + .35*pattern)
                if texture < .2 or line_count < 2:
                    score = min(score, .49)
                candidate = ChipCandidate((x,y,bw,bh), score, method)
                reject_reason=None
                if not position_allowed(candidate.box,card.shape,self.cfg):
                    reject_reason="outside_expected_chip_position"
                elif oversized_and_wide(candidate.box,card.shape,self.cfg):
                    reject_reason="large_and_wide_chip_candidate"
                if reject_reason is not None:
                    rejected.append({"box":candidate.box,"score":score,"method":method,
                                     "relative_center":((x+bw/2)/w,(y+bh/2)/h),
                                     "area_fraction":fraction,"aspect_ratio":aspect,
                                     "reason":reject_reason})
                    continue
                # Deduplicate branches detecting the same physical region.
                def overlap(other: ChipCandidate) -> bool:
                    ox,oy,ow,oh=other.box
                    intersection=max(0,min(x+bw,ox+ow)-max(x,ox))*max(0,min(y+bh,oy+oh)-max(y,oy))
                    return intersection/max(1,bw*bh+ow*oh-intersection)>.50
                duplicate = next((c for c in candidates if overlap(c)), None)
                if duplicate is None:
                    candidates.append(candidate)
                elif candidate.score > duplicate.score:
                    candidates.remove(duplicate)
                    candidates.append(candidate)
        candidates.sort(key=lambda c:c.score, reverse=True)
        for x1,y1,x2,y2 in expected_regions(self.cfg):
            cv2.rectangle(preview,(round(x1*w),round(y1*h)),(round(x2*w),round(y2*h)),(220,100,220),1)
        for item in rejected:
            if item["score"]>=self.cfg["min_score"]:
                x,y,bw,bh=item["box"]
                cv2.rectangle(preview,(x,y),(x+bw,y+bh),(0,0,230),1)
        for candidate in candidates:
            x,y,bw,bh = candidate.box
            cv2.rectangle(preview, (x,y), (x+bw,y+bh), (0,200,255), 2)
            cv2.putText(preview, f"{candidate.score:.2f}", (x,y-4), cv2.FONT_HERSHEY_SIMPLEX, .45, (0,0,255),1)
        debug["candidates"] = preview
        debug["rejected_chip_candidates"] = rejected
        return candidates, debug
