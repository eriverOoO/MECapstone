"""Sources supply BGR frames; vision never depends on a camera driver."""
from pathlib import Path
from typing import Protocol
import cv2
import numpy as np

IMAGE_EXTENSIONS = frozenset((".png", ".jpg", ".jpeg", ".bmp", ".webp"))


def read_image(path: str | Path) -> np.ndarray | None:
    """Unicode-safe image read, including Korean Windows paths."""
    try:
        return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    except (OSError, cv2.error):
        return None


def write_image(path: str | Path, frame: np.ndarray) -> None:
    path = Path(path)
    ok, buffer = cv2.imencode(path.suffix, frame)
    if not ok:
        raise OSError(f"Cannot encode {path}")
    buffer.tofile(str(path))


class FrameSource(Protocol):
    fps: float
    def read(self) -> tuple[bool, np.ndarray | None, int, float]: ...
    def close(self) -> None: ...


class VideoSource:
    def __init__(self, path: str | Path):
        self.path = str(Path(path).resolve())
        self.is_image = Path(path).suffix.lower() in IMAGE_EXTENSIONS
        self.image = read_image(path) if self.is_image else None
        if self.is_image and self.image is None:
            raise OSError(f"Cannot decode image: {path}")
        self.cap = None if self.image is not None else cv2.VideoCapture(self.path)
        if self.image is None and not self.cap.isOpened():
            self.cap.release()
            raise OSError(f"Cannot open input: {path}. See README MOV/FFmpeg instructions.")
        self.fps = 1.0 if self.image is not None else float(self.cap.get(cv2.CAP_PROP_FPS))
        if not np.isfinite(self.fps) or self.fps <= 0:
            self.fps = 30.0
        self.count = 1 if self.image is not None else int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.next_frame = 0

    def read(self) -> tuple[bool, np.ndarray | None, int, float]:
        index = self.next_frame
        if self.image is not None:
            ok, frame = index == 0, self.image.copy() if index == 0 else None
        else:
            ok, frame = self.cap.read()
        if ok:
            self.next_frame += 1
        return ok, frame, index, index / self.fps

    def seek(self, index: int) -> None:
        index = max(0, min(index, max(0, self.count - 1)))
        if self.cap is not None and not self.cap.set(cv2.CAP_PROP_POS_FRAMES, index):
            raise OSError("This codec does not support seeking")
        self.next_frame = index

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()


class CameraSource:
    def __init__(self, device: int, width: int):
        self.cap = cv2.VideoCapture(device)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if not self.cap.isOpened():
            self.cap.release()
            raise OSError(f"Cannot open camera {device}")
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps if np.isfinite(fps) and fps > 0 else 30.0
        self.index = 0
        import time
        self.started = time.monotonic()

    def read(self) -> tuple[bool, np.ndarray | None, int, float]:
        import time
        ok, frame = self.cap.read()
        index = self.index
        self.index += 1
        return ok, frame, index, time.monotonic() - self.started

    def close(self) -> None:
        self.cap.release()


class PiCameraSource:
    """Optional adapter; requires Picamera2 on Raspberry Pi OS."""
    def __init__(self, width: int):
        from picamera2 import Picamera2
        import time
        self.camera = Picamera2()
        # Picamera2 RGB888 arrays use B,G,R byte order for OpenCV.
        self.camera.configure(self.camera.create_video_configuration(main={"size": (width, width * 3 // 4), "format": "RGB888"}))
        self.camera.start()
        self.index, self.fps, self.started = 0, 30.0, time.monotonic()

    def read(self) -> tuple[bool, np.ndarray | None, int, float]:
        import time
        frame = self.camera.capture_array("main")
        index = self.index
        self.index += 1
        return True, frame, index, time.monotonic() - self.started

    def close(self) -> None:
        self.camera.stop()
        self.camera.close()
