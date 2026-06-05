# Phase 0 — keyboard/mouse overlay sanity

Date: 2026-06-05 / 2026-06-06 KST  
Purpose: close the Phase 0 ROADMAP sanity item that asks for keyboard/mouse overlay plausibility on real D2E video.

## Code/image/reservation

- Branch: `codex/phase-0`
- Git SHA on MLXP: `ee21a18be3eac0b74d8f241cbd6ae611e4df5f6f`
- Image: `docker.io/pjh6029/fdm-1-with-d2e:phase0-20260605-ee08fb8@sha256:4b6d2e78f8f6393ca0e8b23af21de50fc852c292cdd2c934cb2a05f31d6555cb`
- Reservation: `rsv-jeonghunpark-20260606-dac111`
- Project/namespace: `production` / `p-production`
- Node/GPU: node `5`, GPU index `[0]`, one H200.
- Status: cancelled after artifact copy.
- Dataset root: `/mnt/ddn/extra-ddn-continuous-gui`; treated as read-only. Outputs were written under repo-local `outputs/`.

## Inputs

- Video: `/mnt/ddn/extra-ddn-continuous-gui/labeled/Apex_Legends/0805_01.mkv`
- MCAP: `/mnt/ddn/extra-ddn-continuous-gui/labeled/Apex_Legends/0805_01.mcap`
- Decoded event counts in overlay script:
  - keyboard: `8262`
  - mouse_move: `77071`
  - mouse_button: `676`
  - scroll: `593`
  - screen: `75629`
- Bins: `29242` at 50ms.
- Dropped events in overlay run: `1` boundary event outside the selected first-screen-to-last-screen span.

## Artifacts

Local copied artifact directory:

- `outputs/phase0/overlay-sanity/20260605-g014-ee21a18/`

Key files:

- `overlay_summary.json`
- `overlay-run.stdout.log`, `overlay-run.stderr.log`
- `git-sha.txt`
- `frames/overlay_01_bin_6328.png`
- `frames/overlay_02_bin_7974.png`
- `frames/overlay_03_bin_8331.png`
- `frames/overlay_04_bin_15614.png`
- `frames/overlay_05_bin_21522.png`
- `frames/overlay_06_bin_23323.png`

MLXP API artifacts:

- `outputs/phase0/mlxp/20260605-g014-overlay-sanity/`

## Method

A bounded cluster-only script decoded real D2E JSON MCAP actions with the repo reader/binning path, selected six active 50ms bins that had nonzero mouse movement plus sparse events, read the corresponding frames from the real `.mkv`, and wrote PNGs with:

- recording/bin/timestamp text;
- aggregate mouse `dx/dy` text;
- keyboard/button/scroll event text;
- yellow center-to-delta arrow.

The script did not write into the dataset tree.

## Visual check

Two representative copied frames were manually inspected locally with `view_image`:

- `overlay_01_bin_6328.png`: Apex FPS scene with a large right/up mouse delta arrow and `VK_162:down` overlay; the overlay is visually coherent with active gameplay.
- `overlay_05_bin_21522.png`: Apex menu/loot scene with small mouse movement, `VK_65:up`, and scroll-down overlays; the overlay is plausible for UI interaction.

Result: keyboard/mouse/scroll overlays are plausible on sampled real D2E frames. This is a sanity visualization, not a quantitative metric or model-quality claim.
