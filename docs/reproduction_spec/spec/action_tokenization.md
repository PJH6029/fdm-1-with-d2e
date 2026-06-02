# Reproduction Detail: Action Tokenization

## Design principle

D2E contains timestamped input events. Multiple events can occur inside one 50ms bin.

Use bin-level action serialization:

```
VideoBin_t
  MOUSE_MOVE token
  sparse event token 1
  sparse event token 2
  ...
  sparse event token K
VideoBin_{t+1}
```

For IDM:

- action slots are replaced by `MASK_ACTION`.

For FDM:

- previous action tokens are provided causally.
- model predicts the next bin’s action tokens.

## Special tokens

```
MASK_ACTION
NO_ACTION
PAD_ACTION
BOS_ACTION
EOS_ACTION
EVENT_OVERFLOW
```

Usage:

- `MASK_ACTION`: IDM masked diffusion input
- `NO_ACTION`: explicit no-op action/event
- `PAD_ACTION`: clip packing padding
- `EVENT_OVERFLOW`: more events occurred in a bin than K slots can store

## Keyboard tokens

Use virtual-key or physical-key codes from D2E.

```
KEY_DOWN_<key>
KEY_UP_<key>
```

## Mouse movement tokens

Use raw HID deltas as the main movement signal.

For each 50ms bin:

```
dx = sum(raw_mouse.last_x)
dy = sum(raw_mouse.last_y)
```

Recommended default:

```
MOUSE_MOVE_BIN_<xbin>_<ybin>
```

Bin design:

- signed exponential bins
- include zero bin
- fit bins on the training set
- use global bins across all games, not per-game bins

Recommended number of bins:

- 49 bins per axis
- 49 x 49 = 2401 compound movement tokens

Ablation:

```
MOUSE_DX_BIN_<i>
MOUSE_DY_BIN_<j>
```

Use separate axis tokens if compound-token sparsity becomes problematic.

## Mouse button tokens

```
MOUSE_LEFT_DOWN
MOUSE_LEFT_UP
MOUSE_RIGHT_DOWN
MOUSE_RIGHT_UP
MOUSE_MIDDLE_DOWN
MOUSE_MIDDLE_UP
```

Optional:

- mouse button state auxiliary head

## Scroll tokens

Use scroll tokens because some games and menus may use wheel input.

Recommended:

```
SCROLL_UP
SCROLL_DOWN
SCROLL_LEFT
SCROLL_RIGHT
```

If scroll magnitude is important:

```
SCROLL_DY_BIN_<k>
SCROLL_DX_BIN_<k>
```

## Cursor / click auxiliary target

Use an auxiliary next-click-position prediction head.

This is not necessarily part of the action token vocabulary.

```
NEXT_CLICK_POSITION_BIN_<x>_<y>
NO_CLICK_WITHIN_H
```

Define target:

```
For each bin t:
  find the next mouse button down event within horizon H.
  if found:
      target = screen coordinate of that click
  else:
      target = NO_CLICK_WITHIN_H
```

Recommended:

- H = 1.0s or 2.0s
- grid = 32 x 18 for 16:9 480p
- ablation = 64 x 36

Loss:

```
L_total = L_action + λ_click * L_next_click_position
```

Apply click-position loss:

- on bins with mouse movement
- or bins where a click occurs within H
- otherwise use `NO_CLICK_WITHIN_H`