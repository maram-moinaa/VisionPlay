# core/gestures/right_hand.py
"""
Right-hand gesture processor.

State machine:
  IDLE
    ├─ fist                      → FIST_HOLD
    ├─ peace sign                → secondary click
    └─ thumb+index pinch         → LEFT_PINCH_PENDING_DRAG

  LEFT_PINCH_PENDING_DRAG
    ├─ pinch released < DRAG_HOLD_SECONDS  → left_click() or double_click() → IDLE
    └─ pinch held ≥ DRAG_HOLD_SECONDS      → drag_start() → DRAGGING

  DRAGGING
    └─ pinch released            → drag_end() → IDLE

  FIST_HOLD
    └─ fist released              → drag_end() → IDLE
"""

import time
import logging
from enum import Enum, auto
from collections.abc import Callable

from config import (
    CAMERA_FPS,
    PINCH_ENTER_RATIO,
    PINCH_RELEASE_RATIO,
    PINCH_DEBOUNCE_SECONDS,
    DRAG_HOLD_SECONDS,
    GESTURE_COOLDOWN_SECONDS,
    DOUBLE_CLICK_WINDOW_S,
    ONE_EURO_MINCUTOFF,
    ONE_EURO_BETA,
    ONE_EURO_DCUTOFF,
)
from core.tracker import Landmark
from core.filter import OneEuroFilter
from core.display import VirtualDesktop, TrackpadZone, map_to_normalized_cursor
from core.actuator import MouseActuator
from core.gestures.utils import dist3d, is_fist, is_open_palm, is_peace_sign

logger = logging.getLogger(__name__)


class _State(Enum):
    IDLE = auto()
    LEFT_PINCH_PENDING_DRAG = auto()
    DRAGGING = auto()
    FIST_HOLD = auto()


class RightHandProcessor:
    """
    Processes right-hand landmarks each frame.
    Call process(landmarks) where landmarks is list[Landmark] | None.
    None means no right hand detected this frame.
    """

    def __init__(
        self,
        actuator: MouseActuator | None,
        desktop: VirtualDesktop,
        trackpad: TrackpadZone,
        on_cursor: Callable[[float, float], None] | None = None,
        on_gesture: Callable[[str], None] | None = None,
    ) -> None:
        self._actuator = actuator
        self._desktop = desktop
        self._trackpad = trackpad
        self._on_cursor = on_cursor
        self._on_gesture = on_gesture
        self._state = _State.IDLE
        self._pinch_start_time: float | None = None
        self._pinch_candidate_since: float | None = None
        self._pinch_release_since: float | None = None
        self._pinch_active = False
        self._two_fingers_active = False
        self._open_hand_active = False
        self._last_click_time: float = 0.0
        self._last_gesture_time: float = 0.0
        self._filter_x = OneEuroFilter(
            freq=float(CAMERA_FPS),
            mincutoff=ONE_EURO_MINCUTOFF,
            beta=ONE_EURO_BETA,
            dcutoff=ONE_EURO_DCUTOFF,
        )
        self._filter_y = OneEuroFilter(
            freq=float(CAMERA_FPS),
            mincutoff=ONE_EURO_MINCUTOFF,
            beta=ONE_EURO_BETA,
            dcutoff=ONE_EURO_DCUTOFF,
        )

    def process(self, landmarks: list[Landmark] | None) -> None:
        if landmarks is None:
            if self._state in (_State.DRAGGING, _State.FIST_HOLD) and self._actuator is not None:
                self._actuator.drag_end()
            if self._state in (_State.DRAGGING, _State.FIST_HOLD) and self._on_gesture is not None:
                self._on_gesture("hold_end")
            if self._open_hand_active and self._on_gesture is not None:
                self._on_gesture("open_hand_end")
            self._state = _State.IDLE
            self._pinch_start_time = None
            self._pinch_candidate_since = None
            self._pinch_release_since = None
            self._pinch_active = False
            self._two_fingers_active = False
            self._open_hand_active = False
            self._filter_x.reset()
            self._filter_y.reset()
            return

        now = time.perf_counter()

        fist = is_fist(landmarks)
        peace = is_peace_sign(landmarks)
        d_thumb_idx = dist3d(landmarks[4], landmarks[8])
        palm_width = dist3d(landmarks[5], landmarks[17])
        pinch_ratio = d_thumb_idx / palm_width if palm_width > 1e-6 else float("inf")
        pinch_threshold = PINCH_RELEASE_RATIO if self._pinch_active else PINCH_ENTER_RATIO
        pinch_detected = not fist and pinch_ratio < pinch_threshold

        if fist:
            self._pinch_active = False
            self._pinch_candidate_since = None
            self._pinch_release_since = None
            self._pinch_start_time = None
        elif pinch_detected:
            self._pinch_release_since = None
            if not self._pinch_active:
                if self._pinch_candidate_since is None:
                    self._pinch_candidate_since = now
                elif now - self._pinch_candidate_since >= PINCH_DEBOUNCE_SECONDS:
                    self._pinch_active = True
                    self._pinch_start_time = self._pinch_candidate_since
        else:
            self._pinch_candidate_since = None
            if self._pinch_active:
                if self._pinch_release_since is None:
                    self._pinch_release_since = now
                elif now - self._pinch_release_since >= PINCH_DEBOUNCE_SECONDS:
                    self._pinch_active = False
                    self._pinch_release_since = None
                    self._pinch_start_time = None

        open_hand = is_open_palm(landmarks) and not self._pinch_active

        if open_hand != self._open_hand_active:
            self._open_hand_active = open_hand
            if self._on_gesture is not None:
                self._on_gesture("open_hand_start" if open_hand else "open_hand_end")

        if fist:
            if self._state != _State.FIST_HOLD:
                if self._state == _State.DRAGGING and self._actuator is not None:
                    self._actuator.drag_end()
                if self._state == _State.DRAGGING and self._on_gesture is not None:
                    self._on_gesture("hold_end")
                self._pinch_start_time = None
                if self._actuator is not None:
                    self._actuator.drag_start()
                if self._on_gesture is not None:
                    self._on_gesture("hold_start")
                self._state = _State.FIST_HOLD
                logger.debug("Fist hold started")
        elif self._state == _State.FIST_HOLD:
            if self._actuator is not None:
                self._actuator.drag_end()
            if self._on_gesture is not None:
                self._on_gesture("hold_end")
            self._state = _State.IDLE
            logger.debug("Fist hold ended")

        two_fingers_started = peace and not self._two_fingers_active
        self._two_fingers_active = peace
        if (
            two_fingers_started
            and self._state == _State.IDLE
            and (now - self._last_gesture_time) >= GESTURE_COOLDOWN_SECONDS
        ):
            if self._on_gesture is not None:
                self._on_gesture("right_click")
            if self._actuator is not None:
                self._actuator.right_click()
            self._last_gesture_time = now
            logger.debug("Secondary selection (two fingers)")

        # ── Left click / drag state machine ───────────────────────────────────
        if self._state == _State.FIST_HOLD:
            pass
        elif self._state == _State.IDLE:
            if self._pinch_active:
                self._state = _State.LEFT_PINCH_PENDING_DRAG

        elif self._state == _State.LEFT_PINCH_PENDING_DRAG:
            if not self._pinch_active:
                # Pinch released — fire click (double if within window)
                if (now - self._last_gesture_time) >= GESTURE_COOLDOWN_SECONDS:
                    if (now - self._last_click_time) <= DOUBLE_CLICK_WINDOW_S and self._last_click_time > 0:
                        if self._on_gesture is not None:
                            self._on_gesture("double_click")
                        if self._actuator is not None:
                            self._actuator.double_click()
                        logger.debug("Double click")
                        self._last_click_time = 0.0  # reset so triple doesn't become double+double
                    else:
                        if self._on_gesture is not None:
                            self._on_gesture("left_click")
                        if self._actuator is not None:
                            self._actuator.left_click()
                        logger.debug("Left click (pinch ratio=%.3f)", pinch_ratio)
                        self._last_click_time = now
                    self._last_gesture_time = now
                self._state = _State.IDLE
                self._pinch_start_time = None

            elif self._pinch_start_time is not None and (now - self._pinch_start_time) >= DRAG_HOLD_SECONDS:
                if self._actuator is not None:
                    self._actuator.drag_start()
                if self._on_gesture is not None:
                    self._on_gesture("hold_start")
                self._state = _State.DRAGGING
                logger.debug("Drag start")

        elif self._state == _State.DRAGGING:
            if not self._pinch_active:
                if self._actuator is not None:
                    self._actuator.drag_end()
                if self._on_gesture is not None:
                    self._on_gesture("hold_end")
                self._state = _State.IDLE
                self._pinch_start_time = None
                logger.debug("Drag end")

        # ── Cursor movement (IDLE and DRAGGING only) ──────────────────────────
        filtered_x = self._filter_x(landmarks[8].x, now)  # index tip
        filtered_y = self._filter_y(landmarks[8].y, now)
        cursor_x, cursor_y = map_to_normalized_cursor(filtered_x, filtered_y, self._trackpad)
        if self._on_cursor is not None:
            self._on_cursor(cursor_x, cursor_y)
        if self._actuator is not None:
            screen_x = round(cursor_x * max(self._desktop.total_width - 1, 0))
            screen_y = round(cursor_y * max(self._desktop.total_height - 1, 0))
            self._actuator.move(screen_x, screen_y)
