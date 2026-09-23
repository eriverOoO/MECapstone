"""인쇄용 ArUco marker PNG를 생성하는 offline 도구."""

import argparse
from pathlib import Path

import config


def generate_markers(
    marker_ids: list[int],
    output_directory: str | Path,
    dictionary_name: str,
    pixel_size: int,
) -> list[Path]:
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError(
            "marker generation requires opencv-contrib-python"
        ) from error
    if not hasattr(cv2, "aruco") or not hasattr(cv2.aruco, dictionary_name):
        raise ValueError(f"unknown or unavailable ArUco dictionary: {dictionary_name}")
    if pixel_size <= 0:
        raise ValueError("pixel_size must be positive")
    dictionary = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, dictionary_name)
    )
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for marker_id in marker_ids:
        if marker_id < 0 or marker_id >= dictionary.bytesList.shape[0]:
            raise ValueError(f"marker id {marker_id} is outside dictionary range")
        # 검출에 필요한 흰색 quiet zone을 전체 크기의 약 10%로 둔다.
        margin = max(pixel_size // 10, 1)
        marker_pixels = pixel_size - 2 * margin
        if marker_pixels <= 0:
            raise ValueError("pixel_size is too small for a marker border")
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, marker_pixels)
        image = cv2.copyMakeBorder(
            marker,
            margin,
            margin,
            margin,
            margin,
            cv2.BORDER_CONSTANT,
            value=255,
        )
        path = directory / f"aruco_{dictionary_name}_{marker_id}.png"
        if not cv2.imwrite(str(path), image):
            raise RuntimeError(f"could not write marker image: {path}")
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate printable ArUco marker PNGs")
    parser.add_argument("ids", nargs="+", type=int)
    parser.add_argument("--output", default="camera_config/generated_markers")
    parser.add_argument("--dictionary", default=config.ARUCO_DICTIONARY)
    parser.add_argument("--pixels", type=int, default=600)
    args = parser.parse_args()
    try:
        paths = generate_markers(
            args.ids, args.output, args.dictionary, args.pixels
        )
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    for path in paths:
        print(f"Marker saved: {path}")


if __name__ == "__main__":
    main()
