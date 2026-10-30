<div align="center">

# AI Air Mouse

### Control your PC with nothing but your hands.

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com/windows)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.35-00897B?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/edge/mediapipe)
[![License](https://img.shields.io/badge/License-MIT-F7CA18?style=for-the-badge)](LICENSE)

**No mouse. No touchpad. No hardware. Just a webcam.**

[Getting Started](#-quick-start) · [Gesture Guide](#-gesture-guide) · [Calibration](#-calibration) · [Architecture](#-architecture) · [Troubleshooting](#-troubleshooting)

</div>

---

## What is this?

AI Air Mouse uses your webcam and [MediaPipe's hand landmark model](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) to track your hands in real time and translate gestures into mouse and keyboard actions — entirely on your device, with zero cloud calls.

The right hand owns the pointer and primary selection; distinct hand postures provide drag, dwell selection, and secondary selection. The left hand optionally controls Windows system shortcuts. Together they support clicks, drag, zoom, window snapping, and more.

```
Webcam → MediaPipe (21 landmarks per hand) → Gesture State Machines → SendInput / pynput → Windows
```

Everything runs in a tight async loop. Frame capture never blocks inference. Cursor smoothing uses the [1-euro filter](https://cristal.univ-lille.fr/~casiez/1euro/) — zero perceptible lag at high speed, zero jitter at rest.

---

## Requirements

| | Minimum | Recommended |
|---|---|---|
| **Python** | 3.12 | 3.13 |
| **Windows** | 10 | 11 |
| **Webcam** | Any DirectShow camera | 60 FPS capable |
| **RAM** | 2 GB | 4 GB+ |
| **Privileges** | Standard user | Administrator (for priority tuning) |

---

## Quick Start

```powershell
git clone https://github.com/Rcidshacker/airmouse.git
cd airmouse

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Verify all subsystems are healthy
.\.venv\Scripts\python test_startup.py

# Launch
.\.venv\Scripts\python main.py
```

> Press **Ctrl+C** to exit. All Windows settings (timer resolution, pointer acceleration, process priority) are automatically restored on shutdown.

On startup you'll see logs like:

```
[INFO] core.tracker:    MediaPipe HandLandmarker initialized (max_hands=2)
[INFO] core.gestures.orchestrator: GestureOrchestrator ready (dual-hand mode)
[INFO] airmouse.main:   Running. Press Ctrl+C to exit.
[INFO] airmouse.main:   FPS: 31.4
```

---

## G3 Company Selection — Web Mode

The local React interface reuses the existing `AsyncCamera`, `HandTracker`, and right-hand gesture state machine. In web mode Python owns the webcam once and sends normalized cursor positions, status, and gesture events; it never sends camera frames or injects OS mouse clicks. The desktop `main.py` mode remains available separately.

### Launch on Windows

Open two PowerShell terminals in the project folder. Do not run desktop mode and web mode at the same time; a process lock prevents both from opening the camera.

**Terminal 1 — Python API and tracker:**

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m web_backend.server
```

**Terminal 2 — React development server:**

```powershell
Set-Location .\frontend
npm install
npm run dev
```

Open `http://localhost:5173` in Chrome. Stop the backend with **Ctrl+C** before launching `.\.venv\Scripts\python.exe main.py` for desktop control.

### Controls and configuration

- **POINT:** Move the cursor with your index finger.
- **OPEN HAND:** Hold an open palm and pause over a card for `DWELL_DURATION_SECONDS` (default **1.5 s**) to select it. The circular indicator shows dwell progress.
- **PINCH:** A thumb-index pinch selects; hold it to drag.
- **FIST:** Hold the primary mouse button until you release the fist.
- **TWO FINGERS:** Secondary-click a card; on the confirmation view, secondary-click goes back.
- Normal mouse, keyboard focus/Enter, **Restart experience**, and the confirmation buttons remain available without a webcam.
- `INVERT_CURSOR_X = True` is the default: the raw OpenCV camera frame is unmirrored, so when you face the camera and move your hand physically right, MediaPipe x decreases. The one inversion in `core/display.py` makes the cursor move right with your hand (selfie-mirror interaction). Set it to `False` only if you prefer the cursor to follow raw camera-image direction. Do not also flip frames or change `FLIP_HANDEDNESS`.
- API binding defaults to loopback (`API_HOST = "127.0.0.1"`, `API_PORT = 8765`); the only allowed development CORS origin is `http://localhost:5173`. The Vite app connects to `ws://127.0.0.1:8765/ws/tracking`.
- If you change the API host, port, or WebSocket path, set `VITE_TRACKING_WS_URL` in `frontend/.env.local` to the matching `ws://...` URL.
- Cursor response uses the existing 1€ filter in both modes. `ONE_EURO_MINCUTOFF = 0.8` improves small-motion response, while `ONE_EURO_BETA = 0.02` lets the filter follow faster movements with less lag; reduce mincutoff if stationary jitter is noticeable, or raise it for faster response. `ONE_EURO_DCUTOFF` remains unchanged. The browser renders incoming positions at display refresh rate with light interpolation instead of re-rendering the React UI on every camera frame; the interpolation is kept close to the filtered camera coordinates to limit added latency. The filter resets when the tracked hand leaves the frame.

### WebSocket event protocol

The backend endpoint is `/ws/tracking`. Every message is one JSON object:

```json
{"type":"cursor","x":0.45,"y":0.62}
{"type":"gesture","name":"left_click"}
{"type":"gesture","name":"right_click"}
{"type":"gesture","name":"double_click"}
{"type":"gesture","name":"open_hand_start"}
{"type":"gesture","name":"open_hand_end"}
{"type":"gesture","name":"hold_start"}
{"type":"gesture","name":"hold_end"}
{"type":"status","camera":"ready","tracking":true,"dwell_seconds":1.5}
{"type":"status","camera":"error","tracking":false,"dwell_seconds":1.5,"message":"..."}
```

Cursor coordinates are normalized to `[0, 1]` and measured from the top-left of the usable viewport. Pinch clicks on release; a long pinch and a held fist emit `hold_start`/`hold_end`. Open-palm transitions gate dwell selection, and the two-finger posture emits one secondary-click event per hold. In web mode events are dispatched to browser UI controls; the OS mouse actuator is not used. Camera ownership, camera/model startup errors, browser disconnects, and server shutdown are handled by the bridge.

The sample company list lives near the top of `frontend/src/main.jsx` and can later be replaced by G3 API data.

---

## Gesture Guide

### Right Hand — Mouse Control

The right hand is always active. Index fingertip drives the cursor.

| Gesture | How to do it | Action |
|---------|-------------|--------|
| **POINT** | Extend the index finger | Pointer / browse |
| **PINCH** | Touch thumb tip to index tip; hold to drag | Grab / select |
| **OPEN HAND** | Extend all fingers and pause over a card | Pause / action (dwell select) |
| **FIST** | Close all fingers; release to stop holding | Maintain / hold |
| **TWO FINGERS** | Extend index and middle; curl the other fingers | Secondary selection |

> **Tip:** Open-hand dwell selection requires the pointer to remain over the same card for the configured 1.5 seconds. Pinch remains available for immediate selection.

---

### Left Hand — System Shortcuts *(optional)*

The left hand adds a system shortcut layer on top of right-hand mouse control. You can ignore it entirely — right-hand behavior is unaffected.

| Gesture | Action |
|---------|--------|
| Open palm (all 5 fingers extended) | `Win+D` — Show Desktop |
| V-sign (index + middle up, others curled) | `Alt+Tab` — Cycle Windows |
| Four fingers (index–pinky up, thumb curled) | `Win+Tab` — Task View |
| Thumb + index pinch | `Win` — Start Menu |
| Fist (held) | Hold `Ctrl` — combine with right-hand click for multi-select |
| Fist (released) | Release `Ctrl` |
| Index pointing + wrist swipe right | `Alt+Left` — Go Back |

> **Ctrl + Click workflow:** Make a left-hand fist to hold Ctrl, then left-click with your right hand to multi-select items. Release the fist to drop Ctrl.

---

### Two-Hand Gestures — Power Actions

Activated only when both hands are visible.

| Gesture | Action |
|---------|--------|
| Both hands pinch + spread wrists apart | `Ctrl+=` — Zoom In |
| Both hands pinch + bring wrists together | `Ctrl+−` — Zoom Out |
| Left open palm + right fist swipe **right** | `Win+Right` — Snap window right |
| Left open palm + right fist swipe **left** | `Win+Left` — Snap window left |
| Both fists held for **1 second** | `Win+L` — Lock Screen |

---

## Calibration

All parameters live in `config.py` — never scattered across modules.

<details>
<summary><b>Cursor feel</b></summary>

| Symptom | Parameter | Fix |
|---------|-----------|-----|
| Cursor shakes at rest | `ONE_EURO_MINCUTOFF` | Decrease → try `0.3` |
| Cursor lags during fast motion | `ONE_EURO_BETA` | Increase → try `0.05` |
| Cursor drifts near edges | `TRACKPAD_MARGIN` | Increase |
| Cursor moves opposite your hand | `INVERT_CURSOR_X` | Toggle once; do not mirror the frame too |

</details>

<details>
<summary><b>Click sensitivity</b></summary>

| Symptom | Parameter | Fix |
|---------|-----------|-----|
| Left click not triggering | `THUMB_INDEX_CLICK_DIST` | Increase → try `0.055` |
| Accidental left clicks | `THUMB_INDEX_CLICK_DIST` | Decrease → try `0.04` |
| Drag activates too quickly | `DRAG_HOLD_SECONDS` | Increase → try `0.5` |

</details>

<details>
<summary><b>Two-hand gestures & zoom</b></summary>

| Symptom | Parameter | Fix |
|---------|-----------|-----|
| Window snap gesture too sensitive | `WRIST_VELOCITY_THRESHOLD` | Increase → try `0.012` |
| Window snap gesture not registering | `WRIST_VELOCITY_THRESHOLD` | Decrease → try `0.005` |
| Zoom fires too easily | `ZOOM_WRIST_DELTA` | Increase → try `0.07` |

</details>

<details>
<summary><b>Performance</b></summary>

| Symptom | Parameter | Fix |
|---------|-----------|-----|
| Low FPS | `CAMERA_WIDTH` / `CAMERA_HEIGHT` | Reduce to `640` / `480` |
| Camera buffer delay | `CAMERA_BUFFER_SIZE` | Keep at `1` |

> MediaPipe dual-hand inference is heavier than single-hand. ~30 FPS at 1280×720 is normal.

</details>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                            main.py                              │
│  Windows OS tuning → inference loop → cleanup on exit           │
└───────────────┬─────────────────────────────────────────────────┘
                │
    ┌───────────┼───────────────────────────────┐
    │           │                               │
    ▼           ▼                               ▼
camera.py   tracker.py                     actuator.py
Async       MediaPipe                      SendInput (move)
DirectShow  HandLandmarker    ──────────►  pynput (click/key)
daemon      → HandsResult
thread      (left, right)
                │
                ▼
        gestures/orchestrator.py
        Routes HandsResult to sub-processors
                │
    ┌───────────┼───────────────┐
    │           │               │
    ▼           ▼               ▼
right_hand  left_hand       two_hand
Pointer     Win shortcuts   Zoom / Snap
Clicks      Alt+Tab         Lock screen
Pinch drag  Ctrl modifier
Open-hand dwell
Fist hold / two-finger secondary
    │
    ▼
filter.py + display.py
1-euro smooth   DPI-aware
cursor          coord map
```

### Why these design choices?

**Distinct selection modes** — Point to browse, open your hand to enable dwell selection, pinch for primary selection, and use two fingers for secondary selection.

**Fist = hold** — A fist maintains the primary mouse button until the hand opens, making drag-and-hold actions explicit.

**`SendInput` over `mouse_event`** — `mouse_event` is a deprecated Vista-era compatibility shim. `SendInput` with `MOUSEEVENTF_VIRTUALDESK` correctly spans all monitors in a virtual desktop.

**DirectShow over MSMF** — `CAP_DSHOW` delivers lower capture latency than the default Media Foundation backend on Windows.

**1-euro filter over Kalman** — Adaptive speed-dependent low-pass filter. Strict reduction in cursor lag vs. Kalman at equivalent jitter suppression (Casiez et al., CHI 2012).

**MediaPipe handedness flip** — MediaPipe labels hands from the camera's point of view. Camera-"Left" = user's right (webcam is a mirror). The tracker flips the label before populating `HandsResult.right`.

---

## Project Structure

```
airmouse/
├── main.py              Entry point — Windows setup + inference loop
├── config.py            Every tunable constant, one file
├── requirements.txt     Dependencies
├── test_startup.py      Smoke tests — run before first use
├── models/              hand_landmarker.task (git-ignored, ~9 MB)
├── web_backend/         FastAPI WebSocket + shared tracking bridge
├── frontend/            React + Vite company selection interface
├── tests/               Coordinate, gesture event, dwell, and protocol tests
└── core/
    ├── camera.py        Async frame capture via daemon thread
    ├── filter.py        1-euro filter implementation
    ├── display.py       Multi-monitor virtual desktop + DPI mapping
    ├── tracker.py       MediaPipe wrapper → HandsResult dataclass
    ├── actuator.py      Mouse + keyboard injection
    └── gestures/
        ├── orchestrator.py   Coordinates all three processors
        ├── right_hand.py     5-state machine: IDLE/PENDING/DRAG/SCROLL/LOCKED
        ├── left_hand.py      System shortcuts + Ctrl modifier state
        ├── two_hand.py       Zoom / snap / lock-screen
        └── utils.py          dist3d, is_fist, is_peace_sign, is_open_palm, …
```

Focused automated checks can be run without opening a camera:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
Set-Location .\frontend
npm test
npm run build
```

---

## Troubleshooting

<details>
<summary><b>Camera fails to open</b></summary>

- Open Device Manager and confirm the webcam appears under **Cameras** or **Imaging devices**
- Try setting `CAMERA_INDEX = 1` or `2` in `config.py` if you have multiple cameras
- Ensure privacy shutters are open on laptops with built-in shutters
- Check that no other app (Teams, Zoom, OBS) has exclusive camera access

</details>

<details>
<summary><b>Cursor maps to wrong screen positions</b></summary>

The app sets `PROCESS_PER_MONITOR_DPI_AWARE` at startup. If you use mixed DPI scaling across monitors:
- Set all displays to the same scale (100% or 125%) for initial testing
- Ensure your primary monitor is set correctly in Windows Display Settings

</details>

<details>
<summary><b>Gestures not recognized</b></summary>

- **Lighting**: Diffuse, even lighting works best. Avoid strong backlighting.
- **Distance**: Keep your hand 40–70 cm from the camera.
- **Background**: High-contrast backgrounds help MediaPipe. Avoid skin-tone walls.
- **Thresholds**: Tweak `THUMB_INDEX_CLICK_DIST` or `WRIST_VELOCITY_THRESHOLD` in `config.py`.

</details>

<details>
<summary><b>Low FPS / stuttering</b></summary>

- Dual-hand MediaPipe inference is ~2× heavier than single-hand — 30 FPS at 1280×720 is expected
- Reduce resolution to 640×480 in `config.py` for ~50% FPS improvement
- Close other webcam-consuming applications
- Run as Administrator for `HIGH_PRIORITY_CLASS` and MMCSS "Games" scheduling

</details>

<details>
<summary><b>Permission warnings in logs</b></summary>

`HIGH_PRIORITY_CLASS` and MMCSS thread registration require Administrator privileges. The application functions normally without elevation but may drop frames under CPU load. Run the terminal as Administrator for best performance.

</details>

---

## License

[MIT License](LICENSE) — do whatever you want, just keep the attribution.
