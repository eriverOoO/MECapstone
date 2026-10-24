import cv2
import numpy as np
from ..models import Status

INLET = {"right": (1., 0.), "left": (-1., 0.), "up": (0., -1.), "down": (0., 1.)}


def order_quad(points: np.ndarray) -> np.ndarray:
    """Cyclic quad with the first edge along the long side (no 180° claim)."""
    points = np.asarray(points, np.float32).reshape(4, 2)
    center = points.mean(axis=0)
    points = points[np.argsort(np.arctan2(points[:, 1]-center[1], points[:, 0]-center[0]))]
    points = np.roll(points, -int(np.argmin(points.sum(axis=1))), axis=0)
    if np.linalg.norm(points[1]-points[0]) < np.linalg.norm(points[2]-points[1]):
        points = np.roll(points, -1, axis=0)
    return points


def project(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    points = np.asarray(points, np.float64).reshape(-1, 2)
    homogeneous = np.column_stack((points, np.ones(len(points)))) @ np.asarray(matrix).T
    if np.any(np.abs(homogeneous[:, 2]) < 1e-8):
        raise ValueError("Point maps to infinity in stage homography")
    result = homogeneous[:, :2] / homogeneous[:, 2:]
    if not np.all(np.isfinite(result)):
        raise ValueError("Nonfinite stage coordinates")
    return result


def classify(quad: np.ndarray, chip_center: tuple[float, float], cfg: dict) -> tuple[Status, str]:
    """Classify in stage coordinates, independent of warp corner polarity."""
    try:
        points = project(np.vstack((quad, chip_center)), np.asarray(cfg["image_to_stage"]))
    except ValueError:
        return Status.UNKNOWN, "invalid_stage_projection"
    card, chip = points[:4], points[4]
    axis = ((card[1]-card[0]) + (card[2]-card[3])) / 2
    length = np.linalg.norm(axis)
    if length < 1e-6:
        return Status.UNKNOWN, "degenerate_card"
    inlet = np.array(INLET[cfg["inlet"]])
    alignment = abs(float(np.dot(axis / length, inlet)))
    if alignment < np.cos(np.radians(cfg["max_axis_angle_deg"])):
        return Status.UNKNOWN, "unexpected_card_axis"
    side = float(np.dot(chip-card.mean(axis=0), inlet)) / (length / 2)
    if abs(side) < cfg["center_dead_zone"]:
        return Status.UNKNOWN, "chip_near_center"
    return (Status.CORRECT, "chip_toward_inlet") if side > 0 else (Status.REVERSED, "chip_away_from_inlet")
