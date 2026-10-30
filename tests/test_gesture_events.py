import unittest
from unittest.mock import Mock
from unittest.mock import patch

from core.display import TrackpadZone, VirtualDesktop
from core.gestures.right_hand import RightHandProcessor
from core.tracker import Landmark


def neutral_hand() -> list[Landmark]:
    points = [Landmark(0.5, 0.5, 0.0) for _ in range(21)]
    points[0] = Landmark(0.5, 0.8, 0.0)
    points[2] = Landmark(0.2, 0.5, 0.0)
    points[4] = Landmark(0.2, 0.3, 0.0)
    points[5] = Landmark(0.38, 0.4, 0.0)
    points[17] = Landmark(0.62, 0.4, 0.0)
    for tip, pip, x in ((8, 6, 0.5), (12, 10, 0.75), (16, 14, 0.85), (20, 18, 0.95)):
        points[pip] = Landmark(x, 0.4, 0.0)
        points[tip] = Landmark(x, 0.2 if tip == 8 else 0.6, 0.0)
    return points


def pinched_hand(distance: float = 0.0) -> list[Landmark]:
    points = neutral_hand()
    points[4] = Landmark(0.5 - distance / 2, 0.25, 0.0)
    points[8] = Landmark(0.5 + distance / 2, 0.25, 0.0)
    return points


def two_fingers_hand() -> list[Landmark]:
    points = neutral_hand()
    points[2] = Landmark(0.2, 0.5, 0.0)
    points[4] = Landmark(0.2, 0.7, 0.0)
    points[12] = Landmark(0.75, 0.2, 0.0)
    return points


def fist_hand() -> list[Landmark]:
    points = neutral_hand()
    points[4] = Landmark(0.2, 0.7, 0.0)
    points[8] = Landmark(0.5, 0.6, 0.0)
    return points


def open_hand() -> list[Landmark]:
    points = neutral_hand()
    for tip in (12, 16, 20):
        points[tip] = Landmark(points[tip].x, 0.2, 0.0)
    return points


class BrowserGestureEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events: list[str] = []
        self.cursors: list[tuple[float, float]] = []
        self.processor = RightHandProcessor(
            actuator=None,
            desktop=VirtualDesktop(1, 1, 1),
            trackpad=TrackpadZone(100, 1180, 100, 620),
            on_cursor=lambda x, y: self.cursors.append((x, y)),
            on_gesture=self.events.append,
        )

    def process_at(self, hand: list[Landmark], timestamp: float) -> None:
        with patch("core.gestures.right_hand.time.perf_counter", return_value=timestamp):
            self.processor.process(hand)

    def test_left_pinch_emits_one_event_on_release_not_while_held(self) -> None:
        pinched = pinched_hand(distance=0.072)

        self.process_at(pinched, 1.0)
        self.process_at(pinched, 1.1)
        self.process_at(pinched, 1.2)
        self.process_at(neutral_hand(), 1.3)
        self.process_at(neutral_hand(), 1.4)

        self.assertEqual(self.events, ["left_click"])

    def test_brief_pinch_and_release_noise_do_not_create_extra_clicks(self) -> None:
        pinched = pinched_hand()
        near_release = pinched_hand(distance=0.13)

        self.process_at(pinched, 1.0)
        self.process_at(neutral_hand(), 1.02)
        self.process_at(pinched, 1.1)
        self.process_at(pinched, 1.16)
        self.process_at(near_release, 1.2)
        self.process_at(pinched, 1.23)
        self.process_at(neutral_hand(), 1.3)
        self.process_at(neutral_hand(), 1.36)

        self.assertEqual(self.events, ["left_click"])

    def test_two_fingers_emits_one_secondary_selection_per_hold(self) -> None:
        two_fingers = two_fingers_hand()
        self.process_at(two_fingers, 2.0)
        self.process_at(two_fingers, 2.5)
        self.process_at(two_fingers, 3.0)
        self.assertEqual(self.events, ["right_click"])
        self.assertTrue(self.cursors)

    def test_open_hand_events_mark_start_and_end_of_dwell_selection(self) -> None:
        hand = open_hand()
        self.process_at(hand, 3.0)
        self.process_at(hand, 3.1)
        self.process_at(neutral_hand(), 3.2)

        self.assertEqual(self.events, ["open_hand_start", "open_hand_end"])

    def test_long_pinch_emits_hold_events_for_dragging(self) -> None:
        pinched = pinched_hand()

        self.process_at(pinched, 3.5)
        self.process_at(pinched, 4.0)
        self.process_at(neutral_hand(), 4.1)

        self.assertEqual(self.events, ["hold_start", "hold_end"])

    def test_fist_holds_until_released_or_hand_leaves_frame(self) -> None:
        fist = fist_hand()
        self.process_at(fist, 4.0)
        self.process_at(fist, 4.1)
        self.process_at(neutral_hand(), 4.2)
        self.process_at(fist, 4.3)
        self.process_at(None, 4.4)

        self.assertEqual(self.events, ["hold_start", "hold_end", "hold_start", "hold_end"])

    def test_desktop_actuator_keeps_left_and_right_click_behavior(self) -> None:
        actuator = Mock()
        processor = RightHandProcessor(
            actuator=actuator,
            desktop=VirtualDesktop(1920, 1080, 1),
            trackpad=TrackpadZone(100, 1180, 100, 620),
        )
        left_pinch = pinched_hand()
        two_fingers = two_fingers_hand()

        for hand, timestamp in (
            (left_pinch, 5.0),
            (neutral_hand(), 5.1),
            (two_fingers, 6.0),
            (two_fingers, 6.6),
        ):
            with patch("core.gestures.right_hand.time.perf_counter", return_value=timestamp):
                processor.process(hand)

        self.assertEqual(actuator.left_click.call_count, 1)
        self.assertEqual(actuator.right_click.call_count, 1)


if __name__ == "__main__":
    unittest.main()
