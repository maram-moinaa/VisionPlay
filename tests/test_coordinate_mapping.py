import unittest
from unittest.mock import patch

from core.display import TrackpadZone, VirtualDesktop, map_to_desktop, map_to_normalized_cursor


class CoordinateMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.trackpad = TrackpadZone(100, 1180, 100, 620)
        self.desktop = VirtualDesktop(1920, 1080, 1)

    def test_default_mapping_follows_user_left_center_right_motion(self) -> None:
        # Facing the raw camera, moving right makes x decrease; the cursor still
        # moves right because selfie-mirror inversion is enabled by default.
        frame_x = (1.0, 0.5, 0.0)
        with patch("core.display.INVERT_CURSOR_X", True):
            mapped = [
                map_to_normalized_cursor(x, 0.5, self.trackpad)
                for x in frame_x
            ]
            desktop_x = [
                map_to_desktop(x, 0.5, self.trackpad, self.desktop)[0]
                for x in frame_x
            ]
        self.assertEqual([point[0] for point in mapped], [0.0, 0.5, 1.0])
        self.assertEqual([point[1] for point in mapped], [0.5, 0.5, 0.5])
        self.assertLess(desktop_x[0], desktop_x[1])
        self.assertLess(desktop_x[1], desktop_x[2])

    def test_non_inverted_mapping_tracks_raw_frame_left_center_right(self) -> None:
        with patch("core.display.INVERT_CURSOR_X", False):
            mapped = [
                map_to_normalized_cursor(x, 0.5, self.trackpad)
                for x in (0.0, 0.5, 1.0)
            ]
        self.assertEqual([point[0] for point in mapped], [0.0, 0.5, 1.0])
        self.assertEqual([point[1] for point in mapped], [0.5, 0.5, 0.5])
        self.assertLess(mapped[0][0], mapped[1][0])
        self.assertLess(mapped[1][0], mapped[2][0])

    def test_configured_inversion_is_applied_once(self) -> None:
        with patch("core.display.INVERT_CURSOR_X", True):
            mapped = [
                map_to_normalized_cursor(x, 0.5, self.trackpad)
                for x in (0.0, 0.5, 1.0)
            ]
            desktop = [
                map_to_desktop(x, 0.5, self.trackpad, self.desktop)[0]
                for x in (0.0, 0.5, 1.0)
            ]
        self.assertEqual([point[0] for point in mapped], [1.0, 0.5, 0.0])
        self.assertGreater(desktop[0], desktop[1])
        self.assertGreater(desktop[1], desktop[2])

    def test_vertical_mapping_remains_top_to_bottom(self) -> None:
        with patch("core.display.INVERT_CURSOR_X", False):
            mapped = [
                map_to_normalized_cursor(0.5, y, self.trackpad)[1]
                for y in (0.0, 0.5, 1.0)
            ]
        self.assertEqual(mapped, [0.0, 0.5, 1.0])

    def test_default_setting_inverts_raw_camera_x(self) -> None:
        from config import INVERT_CURSOR_X

        self.assertTrue(INVERT_CURSOR_X)
        mapped = [
            map_to_normalized_cursor(x, 0.5, self.trackpad)[0]
            for x in (1.0, 0.5, 0.0)
        ]
        self.assertEqual(mapped, [0.0, 0.5, 1.0])


if __name__ == "__main__":
    unittest.main()
