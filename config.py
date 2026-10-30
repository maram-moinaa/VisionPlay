# config.py
# All tunable parameters for the AI Air Mouse system.
# Adjust these to calibrate for different environments; never scatter constants across modules.

# ── Camera ─────────────────────────────────────────────────────────────────────
CAMERA_INDEX = 0                  # Webcam device index
CAMERA_WIDTH = 1280               # Capture resolution width
CAMERA_HEIGHT = 720               # Capture resolution height
CAMERA_FPS = 60                   # Target capture FPS; webcam must support this
CAMERA_BUFFER_SIZE = 1            # DirectShow buffer: 1 = always freshest frame

# ── MediaPipe ──────────────────────────────────────────────────────────────────
MP_MODEL_PATH = "models/hand_landmarker.task"  # float16 Tasks API bundle
MP_MAX_HANDS = 1
MP_DETECTION_CONFIDENCE = 0.7
MP_TRACKING_CONFIDENCE = 0.5

# ── Virtual Trackpad ───────────────────────────────────────────────────────────
# Shrink the active tracking zone inward from webcam edges by this many pixels.
# Prevents the user needing to stretch their hand to screen corners.
TRACKPAD_MARGIN = 100             # pixels, applied to all four edges

# The raw webcam frame is unmirrored, so a user's physical rightward motion
# appears as decreasing MediaPipe x. Invert once here to make the cursor follow
# the user's motion (selfie-mirror behavior). Set False only for raw-image motion.
# This is applied once in core.display; do not mirror the camera frame as well.
INVERT_CURSOR_X = True

# ── 1€ Filter ─────────────────────────────────────────────────────────────────
# Casiez et al. 2012 — adaptive low-pass filter for cursor smoothing.
# mincutoff: lower = more smoothing at rest (reduce jitter)
# beta: higher = less lag at high speed (reduce lag during fast motion)
# dcutoff: derivative smoothing; usually leave at 1.0
ONE_EURO_MINCUTOFF = 0.8           # response at rest: lower smooths more, higher tracks faster
ONE_EURO_BETA = 0.02               # faster movement raises cutoff to reduce motion lag
ONE_EURO_DCUTOFF = 1.0

# ── G3 Web Mode ───────────────────────────────────────────────────────────────
WEB_MODE_ENABLED = True
DWELL_DURATION_SECONDS = 1.5
API_HOST = "127.0.0.1"            # Keep the tracking API local by default
API_PORT = 8765
WEBSOCKET_PATH = "/ws/tracking"
FRONTEND_ORIGIN = "http://localhost:5173"

# ── Gesture Thresholds ────────────────────────────────────────────────────────
# All distances are Euclidean norms of normalized MediaPipe coordinates [0.0–1.0].

# Pinch detection: thumb-index distance as a fraction of palm width (landmarks 5–17).
PINCH_ENTER_RATIO = 0.45          # enter pinch below this normalized distance
PINCH_RELEASE_RATIO = 0.60        # release pinch above this hysteresis threshold
PINCH_DEBOUNCE_SECONDS = 0.05     # ignore brief landmark noise on pinch and release

# Legacy (kept for reference during migration — unused after Task 5)
CLICK_DISTANCE_THRESHOLD = 0.03
RIGHT_CLICK_DISTANCE_THRESHOLD = 0.06

DRAG_HOLD_SECONDS = 0.4           # thumb+index pinch held → drag activates
GESTURE_COOLDOWN_SECONDS = 0.4    # min gap between discrete gesture events

DOUBLE_CLICK_WINDOW_S = 0.4       # second pinch within this window = double click

# Fist detection — all finger tips must be below their PIP joints
FIST_CURL_THRESHOLD = 0.0         # unused numerically; fist = all 5 curled (boolean)

# Two-hand wrist gestures
WRIST_VELOCITY_THRESHOLD = 0.008  # normalized units/s — minimum wrist swipe to register

# Two-hand gestures
ZOOM_WRIST_DELTA    = 0.05        # normalized wrist-to-wrist distance change per zoom tick
LOCK_SCREEN_HOLD_S  = 1.0         # both fists held this long → Win+L

# ── Handedness ────────────────────────────────────────────────────────────────
# MediaPipe Tasks API reports handedness assuming a mirrored (selfie-camera) input,
# meaning "Right" = user's right hand and "Left" = user's left hand.
# OpenCV VideoCapture on Windows returns the raw (unmirrored) frame, so MediaPipe
# already compensates — set FLIP_HANDEDNESS = False.
# If your cursor tracks the WRONG hand (cursor moves when you raise your LEFT hand),
# toggle this to True.
FLIP_HANDEDNESS = False

# ── Debug ─────────────────────────────────────────────────────────────────────
# Set True to open a debug window showing detected landmarks, hand labels (L/R),
# gesture state, and pinch distances. Press Q in the window to quit.
DEBUG_GESTURES = True

# ── Windows OS ────────────────────────────────────────────────────────────────
# Do not change these unless you understand the Windows scheduler implications.
TIMER_RESOLUTION_MS = 1          # Sets Windows multimedia timer floor to 1ms
# psutil priority constant: HIGH_PRIORITY_CLASS = 0x80
# Do NOT use REALTIME_PRIORITY_CLASS (0x100) — it can starve system threads.
PROCESS_PRIORITY = 0x80
