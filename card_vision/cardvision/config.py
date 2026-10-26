"""Load a complete configuration with early validation."""
from pathlib import Path
import math
import yaml

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def load_config(path: str | Path = DEFAULT_PATH) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    for section in ("input", "card", "chip", "quality", "orientation", "stability", "control", "output"):
        if not isinstance(cfg.get(section), dict):
            raise ValueError(f"Missing configuration section: {section}")
    if cfg["input"]["rotation"] not in (0, 90, 180, 270):
        raise ValueError("input.rotation must be 0, 90, 180 or 270")
    if cfg["orientation"]["inlet"] not in ("right", "left", "up", "down"):
        raise ValueError("orientation.inlet must be right/left/up/down")
    for value in (cfg["input"]["width"], cfg["input"]["stride"], cfg["stability"]["frames"],
                  cfg["card"]["normalized_width"], cfg["control"]["max_recheck_frames"],
                  cfg["output"]["failure_interval_frames"]):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError("Sizes and frame counts must be positive integers")
    for key in ("max_flips", "max_rotations"):
        if not isinstance(cfg["control"][key], int) or cfg["control"][key] < 0:
            raise ValueError(f"control.{key} must be a nonnegative integer")
    for key in ("action_timeout_seconds", "observation_timeout_seconds"):
        if cfg["control"][key] <= 0:
            raise ValueError(f"control.{key} must be positive")
    for section in ("card", "chip"):
        if not 0 < cfg[section]["min_area_fraction"] < cfg[section]["max_area_fraction"] < 1:
            raise ValueError(f"Invalid {section} area fractions")
        if not 0 < cfg[section]["min_score"] <= 1:
            raise ValueError(f"Invalid {section} min_score")
    matrix = cfg["orientation"]["image_to_stage"]
    if (len(matrix) != 3 or any(len(row) != 3 for row in matrix)
            or not all(math.isfinite(float(v)) for row in matrix for v in row)):
        raise ValueError("image_to_stage must be a finite 3x3 homography")
    # Determinant without importing vision dependencies.
    a,b,c = matrix[0]; d,e,f = matrix[1]; g,h,i = matrix[2]
    if abs(a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)) < 1e-10:
        raise ValueError("image_to_stage is singular")
    if not 0 < cfg["orientation"]["center_dead_zone"] < 1:
        raise ValueError("center_dead_zone must lie between 0 and 1")
    if not 0 < cfg["orientation"]["max_axis_angle_deg"] < 90:
        raise ValueError("max_axis_angle_deg must lie between 0 and 90")
    roi = cfg["card"]["fixed_roi"]
    if roi is not None and (not isinstance(roi,(list,tuple)) or len(roi) != 4
                            or any(not isinstance(v,int) or isinstance(v,bool) for v in roi)
                            or min(roi[:2]) < 0 or min(roi[2:]) <= 0):
        raise ValueError("fixed_roi must be integer [nonnegative x,y, positive width,height]")
    padding = cfg["card"].setdefault("roi_padding_fraction",.10)
    if (not isinstance(padding,(int,float)) or isinstance(padding,bool)
            or not math.isfinite(padding) or not 0 <= padding <= .50):
        raise ValueError("roi_padding_fraction must be between 0 and 0.50")
    chip = cfg["chip"]
    for key in ("position_filter","edge_candidates","large_wide_filter"):
        if not isinstance(chip.setdefault(key,True),bool):
            raise ValueError(f"chip.{key} must be boolean")
    for key,default,lower,upper in (("large_wide_area_min",.028,0,1),("large_wide_aspect_min",1.50,1,3)):
        value=chip.setdefault(key,default)
        if (not isinstance(value,(int,float)) or isinstance(value,bool)
                or not math.isfinite(value) or not lower<value<upper):
            raise ValueError(f"chip.{key} must be finite and between {lower} and {upper}")
    region = chip.setdefault("expected_region",[.12,.32,.32,.58])
    margin = chip.setdefault("position_margin",[.02,.04])
    if (not isinstance(region,(list,tuple)) or len(region)!=4
            or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in region)
            or not 0<=region[0]<region[2]<.5 or not 0<=region[1]<region[3]<=1):
        raise ValueError("chip.expected_region must be normalized [x1,y1,x2,y2] on the left half")
    if (not isinstance(margin,(list,tuple)) or len(margin)!=2
            or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and 0<=v<=.20 for v in margin)
            or region[2]+margin[0]>=.5):
        raise ValueError("chip.position_margin must contain x/y tolerances in [0,0.20] without joining both regions")
    return cfg
