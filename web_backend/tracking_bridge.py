"""Own the single camera/tracker pipeline and broadcast compact events to WebSockets."""

import asyncio
import logging
import threading
import time
from typing import Any

from config import CAMERA_FPS
from core.camera import AsyncCamera
from core.display import TrackpadZone, VirtualDesktop, build_trackpad_zone
from core.gestures.orchestrator import GestureOrchestrator
from core.tracker import HandTracker
from web_backend.protocol import cursor_message, gesture_message, status_message

logger = logging.getLogger(__name__)


class TrackingBridge:
    """Run existing camera, hand tracker and right-hand gesture state machine once."""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._subscriber_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._latest_status = status_message("starting", False)
        self._tracking = False

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._loop = loop
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="G3Tracking", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.error("Tracking worker did not stop within five seconds")
            else:
                self._thread = None

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=64)
        with self._subscriber_lock:
            self._subscribers.add(queue)
        queue.put_nowait(self._latest_status.copy())
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        with self._subscriber_lock:
            self._subscribers.discard(queue)

    def _publish(self, message: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        if message["type"] == "status":
            with self._status_lock:
                self._latest_status = message
        loop.call_soon_threadsafe(self._broadcast, message)

    def _broadcast(self, message: dict[str, Any]) -> None:
        with self._subscriber_lock:
            subscribers = tuple(self._subscribers)
        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                logger.warning("Slow G3 WebSocket client; dropping its oldest queued event")
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Could not enqueue tracking event for a G3 WebSocket client")

    def _set_tracking(self, tracking: bool) -> None:
        if self._tracking == tracking:
            return
        self._tracking = tracking
        self._publish(status_message("ready", tracking))

    def _run(self) -> None:
        self._publish(status_message("connecting", False))
        failed = False
        try:
            # The browser path uses the same gesture state machine but no desktop actuator.
            desktop = VirtualDesktop(total_width=1, total_height=1, monitor_count=1)
            trackpad: TrackpadZone = build_trackpad_zone()
            with AsyncCamera() as camera, HandTracker() as tracker:
                processor = GestureOrchestrator(
                    actuator=None,
                    desktop=desktop,
                    trackpad=trackpad,
                    on_cursor=lambda x, y: self._publish(cursor_message(x, y)),
                    on_gesture=lambda name: self._publish(gesture_message(name)),
                )
                self._publish(status_message("ready", False))
                last_frame_at = time.monotonic()
                while not self._stop_event.is_set():
                    frame = camera.read()
                    frame_age = camera.frame_age_seconds
                    if frame is None or frame_age is None or frame_age > 5:
                        if time.monotonic() - last_frame_at > 5:
                            raise RuntimeError("Camera opened but stopped producing frames.")
                        self._stop_event.wait(1.0 / CAMERA_FPS)
                        continue
                    last_frame_at = time.monotonic()
                    hands = tracker.process(frame)
                    self._set_tracking(hands.right is not None)
                    processor.process(hands)
        except Exception as exc:
            failed = True
            logger.exception("G3 camera/tracking pipeline failed")
            self._publish(status_message("error", False, str(exc)))
        finally:
            if not failed:
                self._publish(status_message("stopped", False))
