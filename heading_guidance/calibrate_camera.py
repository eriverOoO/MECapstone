"""저장된 chessboard 사진으로 camera calibration JSON을 만드는 offline 도구."""

import argparse
import glob
import json
from pathlib import Path

import config


def calibrate_from_images(
    image_pattern: str,
    output_path: str | Path,
    columns: int,
    rows: int,
    square_size_m: float,
) -> Path:
    """카메라 장치를 열지 않고 입력 이미지 묶음으로 intrinsic을 계산한다."""

    try:
        import cv2
        import numpy as np
    except ImportError as error:
        raise RuntimeError(
            "camera calibration requires opencv-contrib-python and numpy"
        ) from error
    if columns <= 1 or rows <= 1 or square_size_m <= 0.0:
        raise ValueError("invalid chessboard dimensions or square size")
    image_paths = sorted(glob.glob(image_pattern))
    if not image_paths:
        raise ValueError(f"no calibration images matched: {image_pattern}")

    object_template = np.zeros((rows * columns, 3), np.float32)
    object_template[:, :2] = np.mgrid[0:columns, 0:rows].T.reshape(-1, 2)
    object_template *= square_size_m
    object_points = []
    image_points = []
    image_size = None
    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        30,
        0.001,
    )

    for image_path in image_paths:
        image = cv2.imread(image_path)
        if image is None:
            continue
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image_size = (gray.shape[1], gray.shape[0])
        found, corners = cv2.findChessboardCorners(gray, (columns, rows))
        if not found:
            continue
        refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        object_points.append(object_template.copy())
        image_points.append(refined)

    if image_size is None or len(object_points) < 5:
        raise ValueError(
            "at least five readable images with a detected chessboard are required"
        )
    rms, camera_matrix, distortion, _, _ = cv2.calibrateCamera(
        object_points, image_points, image_size, None, None
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "calibrated": True,
        "image_width": image_size[0],
        "image_height": image_size[1],
        "camera_matrix": camera_matrix.tolist(),
        "distortion_coefficients": distortion.reshape(-1).tolist(),
        "rms_reprojection_error": float(rms),
        "images_used": len(object_points),
        "board_inner_corners": [columns, rows],
        "square_size_m": square_size_m,
    }
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline chessboard camera calibration")
    parser.add_argument("image_pattern", help='glob pattern, e.g. "calibration/*.jpg"')
    parser.add_argument("--output", default="camera_config/camera_calibration.json")
    parser.add_argument("--columns", type=int, default=config.CALIBRATION_BOARD_COLUMNS)
    parser.add_argument("--rows", type=int, default=config.CALIBRATION_BOARD_ROWS)
    parser.add_argument(
        "--square-size-m", type=float, default=config.CALIBRATION_SQUARE_SIZE_M
    )
    args = parser.parse_args()
    try:
        output = calibrate_from_images(
            args.image_pattern,
            args.output,
            args.columns,
            args.rows,
            args.square_size_m,
        )
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Calibration saved: {output}")


if __name__ == "__main__":
    main()

