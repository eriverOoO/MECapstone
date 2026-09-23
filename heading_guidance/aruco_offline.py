"""실제 camera 없이 저장 이미지에서 ArUco 검출을 확인하는 CLI."""

import argparse

import config
from vision.aruco_detector import ArucoDetector
from vision.configuration import CameraCalibration


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect ArUco markers in a saved image")
    parser.add_argument("image", help="input image path")
    parser.add_argument("--calibration", default=config.CAMERA_CALIBRATION_PATH)
    parser.add_argument("--without-pose", action="store_true", help="detect ID/corners only")
    args = parser.parse_args()

    try:
        import cv2
    except ImportError as error:
        raise SystemExit(
            "Install optional vision dependencies: pip install -r requirements-vision.txt"
        ) from error
    frame = cv2.imread(args.image)
    if frame is None:
        raise SystemExit(f"Could not read image: {args.image}")
    calibration = (
        None if args.without_pose else CameraCalibration.from_json(args.calibration)
    )
    if calibration is not None and not calibration.calibrated:
        raise SystemExit(
            "The example calibration is not valid for measurements. Calibrate the real camera "
            "or use --without-pose for ID/corner detection only."
        )
    detector = ArucoDetector(calibration=calibration)
    detections = detector.detect(frame)
    if not detections:
        print("No ArUco markers detected")
        return
    for detection in detections:
        print(detection)


if __name__ == "__main__":
    main()

