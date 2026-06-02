# Timebase and Sequence Construction

## Base timestep

Use non-overlapping 50ms bins.

Reason:

- D2E official-style IDM evaluation uses 50ms temporal bins.
- 50ms corresponds to 20Hz action prediction.
- It is tractable across all game types and aligns keyboard/mouse events with video.

## Video sampling

For each 50ms bin:

```
60fps raw video
→ 20fps sampled visual stream
→ one visual timestep per 50ms action bin
```

## Event aggregation

For each 50ms bin:

- aggregate raw mouse HID deltas:
    - sum `last_x`
    - sum `last_y`
- collect keyboard events:
    - key press
    - key release
- collect mouse button events:
    - left/right/middle down
    - left/right/middle up
- collect scroll events if available
- collect optional state:
    - keyboard state
    - mouse button state
    - cursor absolute position
    - active window / game process metadata

# Reproduction Detail: Fixed Action Slots per Bin

Because multiple events can happen inside one 50ms bin, use fixed K action slots.

Recommended default:

```
K = 8 sparse event slots per 50ms bin
```

Per-bin serialization:

```
[MOUSE_MOVE_BIN]
[EVENT_SLOT_1]
[EVENT_SLOT_2]
...
[EVENT_SLOT_K]
```

Ordering:

1. mouse movement token first
2. discrete events sorted by timestamp
3. remaining slots filled with `NO_ACTION`
4. sequence padding uses `PAD_ACTION`

Overflow policy:

- preserve mouse button events
- preserve key down events
- preserve key up events if capacity remains
- otherwise emit `EVENT_OVERFLOW`
- log overflow rate globally and per game
- increase K if overflow rate exceeds 0.1%

Ablation:

- K = 4
- K = 8
- K = 16