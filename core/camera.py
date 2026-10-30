# core/camera.py
"""
Asynchronous frame capture using a dedicated daemon thread.

Problem: cv2.VideoCapture.read() is a blocking call. If it blocks in the
main inference thread, every frame waits for the camera's USB transfer to
complete before MediaPipe can start. At 60fps this is ~16ms of forced wait.

Solution: A dedicated thread reads frames as fast as the camera produces them
and drops them into a shared slot. The main thread takes whatever is in the
slot — always the most recent frame — and never waits on I/O.
"""

import threading
import time
import logging
import os
from pathlib import Path

import cv2

from config import (
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    CAMERA_FPS,
    CAMERA_BUFFER_SIZE,
)

logger = logging.getLogger(__name__)


class AsyncCamera:
    """
    Thread-safe frame source backed by a dedicated capture thread.

    Usage:
        cam = AsyncCamera()
        cam.start()
        frame = cam.read()  # always returns latest, never blocks
        cam.stop()

    Context manager protocol supported for clean resource management.
    """

    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._frame = None
        self._last_frame_at: float | None = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock_file = None

    def _acquire_process_lock(self) -> None:
        """Prevent the desktop and web entry points opening the webcam together."""
        lock_path = Path(__file__).resolve().parents[1] / ".airmouse-camera.lock"
        lock_file = lock_path.open("a+b")
        lock_file.seek(0, 2)
        if lock_file.tell() == 0:
            lock_file.write(b"0")
            lock_file.flush()
        lock_file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            lock_file.close()
            raise RuntimeError(
                "Another AirMouse process already owns the webcam. Close desktop or web mode first."
            ) from exc
        self._lock_file = lock_file

    def _release_process_lock(self) -> None:
        if self._lock_file is None:
            return
        try:
            self._lock_file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            self._lock_file.close()
            self._lock_file = None

    def start(self) -> "AsyncCamera":
        """Open the camera and start the capture thread."""
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Camera already started")
        self._stop_event.clear()
        self._acquire_process_lock()
        try:
            # CAP_DSHOW: DirectShow backend — lower latency than MSMF (default on Windows)
            self._cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
            if not self._cap.isOpened():
                raise RuntimeError(
                    f"Cannot open camera index {CAMERA_INDEX} via DirectShow. "
                    "Verify the webcam is connected and its driver exposes a DirectShow interface."
                )

            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self._cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, CAMERA_BUFFER_SIZE)

            actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
            logger.info("Camera opened: %dx%d @ %.1f fps", actual_w, actual_h, actual_fps)

            self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="CameraCapture")
            self._thread.start()
            return self
        except Exception:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            self._release_process_lock()
            raise

    def _capture_loop(self) -> None:
        """Run in background thread. Grab frames as fast as hardware allows."""
        while not self._stop_event.is_set():
            try:
                ret, frame = self._cap.read()
            except Exception as e:
                logger.error("Camera read exception: %s", e)
                time.sleep(0.01)
                continue
            if not ret:
                logger.warning("Frame grab failed — camera disconnected?")
                self._stop_event.wait(timeout=0.01)
                continue
            with self._lock:
                self._frame = frame
                self._last_frame_at = time.monotonic()

    def read(self):
        """Return the most recent frame. Returns None until the first frame arrives."""
        with self._lock:
            return self._frame

    @property
    def frame_age_seconds(self) -> float | None:
        with self._lock:
            if self._last_frame_at is None:
                return None
            return time.monotonic() - self._last_frame_at

    def stop(self) -> None:
        """Signal the capture thread to stop and release hardware resources."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self._thread is not None:
            self._thread = None
        self._release_process_lock()
        logger.info("Camera released")

    def __enter__(self) -> "AsyncCamera":
        return self.start()

    def __exit__(self, *_) -> None:
        self.stop()
