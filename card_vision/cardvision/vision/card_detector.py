"""Find the actual card inside an optional, generously padded stage window."""
from dataclasses import dataclass
import cv2
import numpy as np
from .geometry import order_quad


@dataclass
class CardResult:
    quad: np.ndarray | None
    score: float
    normalized: np.ndarray | None
    inverse: np.ndarray | None
    debug: dict


class CardDetector:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def detect(self, frame: np.ndarray) -> CardResult:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 45, 140)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        debug = {"gray": gray, "edges": edges}
        height, width = gray.shape
        quad, score = None, 0.0
        x0,y0,x1,y1 = 0,0,width,height
        if self.cfg["fixed_roi"] is not None:
            x,y,w,h = self.cfg["fixed_roi"]
            padding = self.cfg.get("roi_padding_fraction", .10)
            padx,pady = round(w*padding),round(h*padding)
            x0,y0 = max(0,x-padx),max(0,y-pady)
            x1,y1 = min(width,x+w+padx),min(height,y+h+pady)
            if x1-x0 < 8 or y1-y0 < 8:
                return CardResult(None, 0, None, None, debug)
            debug["inspection_roi"] = (x0,y0,x1-x0,y1-y0)
        # The window bounds are never used as the card corners. Detection inside
        # the window verifies presence and preserves chip-to-card coordinates.
        contours, _ = cv2.findContours(edges[y0:y1,x0:x1], cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        annotated = frame.copy()
        offset = np.array([x0,y0],np.float32)
        cv2.drawContours(annotated, contours, -1, (150, 90, 30), 1, offset=(x0,y0))
        if self.cfg["fixed_roi"] is not None:
            cv2.rectangle(annotated,(x0,y0),(x1-1,y1-1),(80,180,80),2)
        debug["contours"] = annotated
        candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            # Keep area thresholds in full processing-image units regardless of padding.
            if not self.cfg["min_area_fraction"] < area/(width*height) < self.cfg["max_area_fraction"]:
                continue
            approx = cv2.approxPolyDP(contour, .025*cv2.arcLength(contour, True), True)
            if len(approx) != 4 or not cv2.isContourConvex(approx):
                continue
            candidate = order_quad(approx)
            if (candidate[:,0].min() < 3 or candidate[:,1].min() < 3
                    or candidate[:,0].max() > x1-x0-4 or candidate[:,1].max() > y1-y0-4):
                continue
            sides = np.linalg.norm(candidate-np.roll(candidate, -1, axis=0), axis=1)
            ratio = (sides[0]+sides[2]) / max(1., sides[1]+sides[3])
            error = abs(ratio-self.cfg["aspect_ratio"]) / self.cfg["aspect_ratio"]
            if error > self.cfg["aspect_tolerance"]:
                continue
            rectangularity = area/max(1., np.prod(cv2.minAreaRect(contour)[1]))
            quality = float(.6*(1-error) + .4*min(1., rectangularity))
            candidates.append((area, quality, candidate+offset))
        if candidates:
            # Reject two distinct card-sized objects, but tolerate duplicate edge contours.
            candidates.sort(key=lambda c: c[0], reverse=True)
            area, score, quad = candidates[0]
            for other_area, _, other in candidates[1:]:
                if other_area > .6*area and np.linalg.norm(other.mean(axis=0)-quad.mean(axis=0)) > .15*np.sqrt(area):
                    return CardResult(None, 0, None, None, debug)
        if quad is None or score < self.cfg["min_score"]:
            return CardResult(None, score, None, None, debug)
        w = self.cfg["normalized_width"]
        h = round(w/self.cfg["aspect_ratio"])
        destination = np.array([[0,0], [w-1,0], [w-1,h-1], [0,h-1]], np.float32)
        transform = cv2.getPerspectiveTransform(quad.astype(np.float32), destination)
        normalized = cv2.warpPerspective(frame, transform, (w,h))
        debug["card"] = normalized
        return CardResult(quad, score, normalized, np.linalg.inv(transform), debug)
