import asyncio
import unittest

from fastapi.testclient import TestClient

from config import DWELL_DURATION_SECONDS, FRONTEND_ORIGIN
from web_backend.protocol import cursor_message, gesture_message, status_message
from web_backend.server import create_app


class FakeBridge:
    def start(self, _loop) -> None:
        pass

    def stop(self) -> None:
        pass

    def subscribe(self):
        queue: asyncio.Queue = asyncio.Queue()
        queue.put_nowait(cursor_message(0.45, 0.62))
        queue.put_nowait(gesture_message("left_click"))
        return queue

    def unsubscribe(self, _queue) -> None:
        pass


class WebProtocolTests(unittest.TestCase):
    def test_cursor_gesture_and_status_shapes(self) -> None:
        cursor = cursor_message(0.45, 0.62)
        gesture = gesture_message("left_click")
        status = status_message("ready", True)
        self.assertEqual(cursor, {"type": "cursor", "x": 0.45, "y": 0.62})
        self.assertEqual(gesture, {"type": "gesture", "name": "left_click"})
        self.assertEqual(status["type"], "status")
        self.assertEqual(status["camera"], "ready")
        self.assertTrue(status["tracking"])
        self.assertEqual(status["dwell_seconds"], DWELL_DURATION_SECONDS)

    def test_websocket_sends_normalized_cursor_event(self) -> None:
        with TestClient(create_app(FakeBridge())) as client:
            with client.websocket_connect(
                "/ws/tracking",
                headers={"origin": FRONTEND_ORIGIN},
            ) as websocket:
                self.assertEqual(
                    websocket.receive_json(),
                    {"type": "cursor", "x": 0.45, "y": 0.62},
                )
                self.assertEqual(
                    websocket.receive_json(),
                    {"type": "gesture", "name": "left_click"},
                )


if __name__ == "__main__":
    unittest.main()
