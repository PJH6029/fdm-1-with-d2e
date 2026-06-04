# Dataset: D2E

Paper link: https://worv-ai.github.io/d2e/

Dataset link: https://huggingface.co/datasets/open-world-agents/D2E-480p

## Reproduction anchors

- Public D2E-480p release: 267 hours, 29 PC games, 480p 60fps.
- Includes synchronized video/audio plus keyboard/mouse/window events in OWAMcap/MCAP.
- Official D2E-style IDM evaluation uses non-overlapping 50ms bins with mouse Pearson X/Y, mouse scale ratio X/Y, mouse-button accuracy, and keyboard key accuracy.
- Public reference model: `open-world-agents/Generalist-IDM-1B`; use it as the IDM reference objective. Naive priors are sanity checks only.
- Canonical reproduction spec should use those metrics as the primary offline action metrics and keep extra metrics diagnostic.


## Video + Audio

- H.264 encoding
- 480p 60fps
- Fixed 0.5s keyframe intervals and disabled B-frame for efficient random seek without sequential decoding
- Includes: FPS, 3D, 2D, top-down, sandbox, survival, platformer, farming, driving, UI-heavy, non-gameplay-like segments

## Input Events

- Keyboard: press/release + key state
- Mouse: clicks, screen coordinates, raw HID deltas, button state
- Active window info
- All with nanosecond timestamps synchronized to video frames

## OWAMcap format

- Indexed for fast random access
- crash-safe writes
- standardized message schemas

## MCAP fields

| **Topic** | **Message Type** | **Description** |
| --- | --- | --- |
| `screen` | `desktop/ScreenCaptured` | Frame timestamp + MediaRef pointer to video |
| `keyboard` | `desktop/KeyboardEvent` | Key press/release with **virtual key code** |
| `keyboard/state` | `desktop/KeyboardState` | Currently pressed keys |
| `mouse` | `desktop/MouseEvent` | Mouse clicks and screen coordinates |
| `mouse/raw` | `desktop/RawMouseEvent` | Raw HID movement (**→ why raw?**) |
| `mouse/state` | `desktop/MouseState` | Current position and button state |
| `window` | `desktop/WindowInfo` | Active window title, rect, and handle |