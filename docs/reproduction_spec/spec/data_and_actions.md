# D2E Data and Action Tokenization

Canonical source: `../CANONICAL_SPEC.md`.

## Role

D2E provides timestamped gameplay video and input events. This spec defines the read-only dataset contract, canonical 50ms timebase, event aggregation, and serialized action tokens used by IDM/FDM training, evaluation, and harness execution.

## Dataset layout

In MLXP pods, the source dataset is read-only:

```text
/mnt/ddn/extra-ddn-continuous-gui/
  labeled/<game-name>/<recording>.mkv
  labeled/<game-name>/<recording>.mcap
  unlabeled/<game-name>/<video>.mkv
  labeled/.source-metadata/
  unlabeled/.source-metadata/
```

Do not write derived files into this tree. `.source-metadata/` is provenance/verification metadata, not model input.

## Timebase and video sampling

Use non-overlapping `50ms` bins as the canonical action timestep.

Reasons:

- matches D2E's public evaluation protocol;
- yields a tractable 20Hz action stream;
- aligns D2E 60fps video with keyboard/mouse events without pretending to recover every video frame action.

For every 50ms bin:

```text
60fps D2E video → one visual timestep per action bin
```

Implementation can use frame sampling, short-window pooling, or a temporal resampler, but the downstream token/action sequence must be aligned to 50ms bins.

## Event aggregation

For each bin, collect:

- raw mouse HID deltas (`last_x`, `last_y`) summed over the bin;
- keyboard press/release events;
- mouse button down/up events;
- scroll events if present;
- optional state features for diagnostics or auxiliary heads: key state, button state, cursor absolute position, active window.

## Required manifests

Commit deterministic manifests for:

- all recordings and durations;
- train/validation/test splits;
- held-out-game splits;
- data-scale subsets (`10%`, `50%`, `100%`);
- per-game/category labels;
- action distribution summaries.

## Serialized action sequence

The model consumes/produces a serialized 50ms-bin action sequence that can be converted back to MCAP-like keyboard/mouse events for evaluation and harness execution.

```text
VideoBin_t
  MOUSE_MOVE_BIN_<xbin>_<ybin>
  EVENT_SLOT_1
  ...
  EVENT_SLOT_K
VideoBin_{t+1}
```

For IDM, target action slots are replaced by `MASK_ACTION`. For FDM, previous action tokens are causal context and the next bin's action tokens are the target.

## Fixed action slots

Use fixed action slots per 50ms bin:

```text
[MOUSE_MOVE_BIN]
[EVENT_SLOT_1]
...
[EVENT_SLOT_K]
```

Default `K = 8`.

Ordering:

1. mouse movement token first;
2. discrete events sorted by timestamp;
3. remaining slots filled with `NO_ACTION`;
4. sequence packing uses `PAD_ACTION`, not `NO_ACTION`;
5. overflow emits/logs `EVENT_OVERFLOW`.

Overflow policy:

- preserve mouse button events;
- preserve key-down events;
- preserve key-up events if capacity remains;
- otherwise emit `EVENT_OVERFLOW` and log the original event count;
- increase `K` only if overflow exceeds `0.1%` of bins or harms sparse-event metrics.

## Special tokens

```text
MASK_ACTION
NO_ACTION
PAD_ACTION
BOS_ACTION
EOS_ACTION
EVENT_OVERFLOW
```

- `MASK_ACTION`: IDM masked-action input.
- `NO_ACTION`: real no-op event slot inside a valid 50ms bin.
- `PAD_ACTION`: sequence packing padding only.
- `EVENT_OVERFLOW`: capacity exceeded in a bin; must be logged.

## Keyboard and button tokens

Use D2E virtual-key/physical-key identifiers consistently across all games:

```text
KEY_DOWN_<key>
KEY_UP_<key>
MOUSE_LEFT_DOWN
MOUSE_LEFT_UP
MOUSE_RIGHT_DOWN
MOUSE_RIGHT_UP
MOUSE_MIDDLE_DOWN
MOUSE_MIDDLE_UP
```

Key repeats must be represented from observed events, not inferred unless the MCAP schema explicitly records repeat state.

## Mouse movement tokens

Default movement signal: raw HID deltas summed over the 50ms bin.

```text
dx = sum(raw_mouse.last_x)
dy = sum(raw_mouse.last_y)
```

Default token:

```text
MOUSE_MOVE_BIN_<xbin>_<ybin>
```

Binning:

- 49 signed exponential bins per axis, including zero;
- fit bin boundaries on the training split only;
- use global bins across games;
- normalize by screen width/height where absolute pixel scale varies.

Ablation if sparsity is a problem:

```text
MOUSE_DX_BIN_<i>
MOUSE_DY_BIN_<j>
```

## Scroll tokens

Default:

```text
SCROLL_UP
SCROLL_DOWN
SCROLL_LEFT
SCROLL_RIGHT
```

Magnitude bins are optional and should be added only if scroll-heavy games/menus show metric failures.

## Auxiliary click-position target

The next-click target is an auxiliary head, not a required action token.

```text
NEXT_CLICK_POSITION_BIN_<x>_<y>
NO_CLICK_WITHIN_H
```

Default:

- horizon `H = 1s`;
- grid `32 x 18` for 16:9 480p;
- apply loss only on movement bins or bins with a click within `H`, plus a calibrated `NO_CLICK_WITHIN_H` class.

Loss:

```text
L_total = L_action + λ_click * L_next_click_position
```

The click auxiliary is promoted only if it improves mouse trajectory or harness stability.
