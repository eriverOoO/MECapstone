import time
import cv2
import numpy as np
from ..models import Observation, Status
from .card_detector import CardDetector
from .chip_detector import ChipDetector
from .geometry import classify, project
from .temporal import Stabilizer


class VisionPipeline:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.card = CardDetector(cfg["card"])
        self.chip = ChipDetector(cfg["chip"])
        self.previous = None

    def reset(self) -> None:
        self.previous = None

    def prepare(self, frame: np.ndarray) -> np.ndarray:
        target = self.cfg["input"]["width"]
        h,w = frame.shape[:2]
        # Preserve aspect ratio; never stretch the card into another orientation.
        frame = cv2.resize(frame, (target, max(1,round(h*target/w))))
        rotation = self.cfg["input"]["rotation"]
        if rotation:
            frame = cv2.rotate(frame, {90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}[rotation])
        return cv2.flip(frame,1) if self.cfg["input"]["mirror"] else frame

    def process_image(self, frame: np.ndarray) -> tuple[np.ndarray, Observation]:
        """Analyze one independent image; motion/stability are not measurable here."""
        return self.process(frame, 0, 0.0, still_image=True)

    def process(self, frame: np.ndarray, index: int, timestamp: float, *, still_image: bool = False) -> tuple[np.ndarray, Observation]:
        started = time.perf_counter()
        frame = self.prepare(frame)
        obs = Observation(index, timestamp)
        result = self.card.detect(frame)
        obs.debug = result.debug
        obs.inspection_roi = result.debug.get("inspection_roi")
        gray = result.debug["gray"]
        if still_image:
            motion = 0.0
        elif self.previous is None or self.previous.shape != gray.shape:
            motion = float("inf")
        else:
            difference = cv2.absdiff(gray,self.previous)
            if obs.inspection_roi is not None:
                x,y,w,h = obs.inspection_roi
                difference = difference[y:y+h,x:x+w]
            motion = float(np.mean(difference))
        if not still_image:
            self.previous = gray.copy()
        if result.quad is not None:
            obs.card_detected, obs.card_quad, obs.card_score = True, result.quad, result.score
            card_gray = cv2.cvtColor(result.normalized,cv2.COLOR_BGR2GRAY)
            q = self.cfg["quality"]
            blur = float(cv2.Laplacian(card_gray,cv2.CV_64F).var())
            brightness = float(card_gray.mean())
            clipped = float(np.mean((card_gray < 8) | (card_gray > 248)))
            candidates, debug = self.chip.detect(result.normalized)
            obs.debug.update(debug)
            obs.debug["quality"] = {"blur_variance":blur,"brightness":brightness,"clipped_fraction":clipped,"motion":None if still_image else motion}
            if candidates:
                best = candidates[0]
                obs.score = best.score
                x,y,w,h = best.box
                corners = np.array([[x,y],[x+w,y],[x+w,y+h],[x,y+h]], np.float32)
                obs.chip_polygon = project(corners, result.inverse)
                center = project(np.array([[x+w/2,y+h/2]]),result.inverse)[0]
                obs.chip_box = best.box
                obs.chip_center = tuple(float(v) for v in center)
                ch,cw = result.normalized.shape[:2]
                obs.chip_relative = ((x+w/2)/cw,(y+h/2)/ch)
                # Detection is separate from whether this frame may drive an action.
                obs.chip_detected = (best.score >= self.cfg["chip"]["min_score"] and
                                     (len(candidates)==1 or best.score-candidates[1].score >= self.cfg["chip"]["ambiguity_margin"]))
            # Even a card without a chip must have its long axis aligned to the
            # inlet. A 90-degree reverse-side card must not request a FLIP.
            axis_probe = tuple((result.quad[1]+result.quad[2])/2)
            _, axis_reason = classify(result.quad, axis_probe, self.cfg["orientation"])
            if blur < q["min_blur_variance"] or not q["min_brightness"] < brightness < q["max_brightness"] or clipped > q["max_clipped_fraction"]:
                obs.reason = "low_image_quality"
            elif motion > q["max_motion"]:
                obs.reason = "motion_or_first_frame"
            elif axis_reason in ("unexpected_card_axis", "invalid_stage_projection", "degenerate_card"):
                obs.reason = axis_reason
            elif not candidates:
                obs.status, obs.reason, obs.score = Status.CHIP_NOT_VISIBLE, "no_chip_candidate", result.score
            else:
                if best.score < self.cfg["chip"]["min_score"]:
                    obs.reason = "weak_chip_candidate"
                elif len(candidates)>1 and best.score-candidates[1].score < self.cfg["chip"]["ambiguity_margin"]:
                    obs.reason = "ambiguous_chip_candidates"
                else:
                    obs.status, obs.reason = classify(result.quad, obs.chip_center, self.cfg["orientation"])
        obs.processing_ms = (time.perf_counter()-started)*1000
        return frame, obs
