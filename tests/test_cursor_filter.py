import unittest

from core.filter import OneEuroFilter


class CursorFilterTests(unittest.TestCase):
    def test_first_value_is_immediate(self) -> None:
        filter_ = OneEuroFilter(freq=60, mincutoff=0.8, beta=0.02)
        self.assertEqual(filter_(0.73, timestamp=1.0), 0.73)

    def test_reset_drops_stale_position_and_timing(self) -> None:
        filter_ = OneEuroFilter(freq=60, mincutoff=0.8, beta=0.02)
        filter_(0.1, timestamp=1.0)
        filter_(0.2, timestamp=1.02)
        filter_.reset()
        self.assertEqual(filter_(0.9, timestamp=10.0), 0.9)


if __name__ == "__main__":
    unittest.main()
