import unittest

from core.camera import AsyncCamera


class CameraOwnershipTests(unittest.TestCase):
    def test_only_one_airmouse_instance_can_own_camera(self) -> None:
        owner = AsyncCamera()
        contender = AsyncCamera()
        owner._acquire_process_lock()
        try:
            with self.assertRaisesRegex(RuntimeError, "already owns the webcam"):
                contender._acquire_process_lock()
        finally:
            owner._release_process_lock()
            contender._release_process_lock()


if __name__ == "__main__":
    unittest.main()
