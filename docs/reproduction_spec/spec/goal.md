# Goal: FDM-1 Reproductionw with D2E dataset

D2E에서 다루는 모든 게임에 대해 FDM-1 style approach가 재현 가능하고 충분한 성능이 나오는지 확인한다.

이 PoC의 목표는 단순히 한 번의 end-to-end run을 성공시키는 것이 아니다.

목표는 **Video Encoder / IDM / FDM 각 training stage 별로 현실적인 candidates를 evaluation metrics을 기준으로 ablate하고**, 아래 Sub goals을 달성하고, 최종적으로는 SoTA Game Play Agent를 구축하는 것이다.

FDM-1 technical report에서 공개되지 않은 training recipe의 gap을 채우기 위해 여러 각도의 exploration과 novel approach가 필요하다.

## Sub Goals

1. D2E의 heterogeneous game distribution 전체에서 FDM-1 style의 video encoder / IDM / FDM pipeline을 end-to-end 구성
2. IDM이 2D, 3D, FPS, open-world, sandbox, top-down, side-scroller, UI/menu-heavy gameplay 전반에 대해 action pseudo-label을 생성
3. IDM pseudo-label로 학습한 FDM이 GT action label로 학습한 FDM에 근접
4. FDM이 특정 게임에 overfit하지 않고 held-out game에서도 non-trivial action prediction을 수행
5. FDM-1 방식의 IDM이 D2E paper에서 제시된 G-IDM의 성능 metric에 근접하거나 초과 달성
6. FDM-1 방식의 FDM이 *TODO*에서 제시된 *TODO*의 성능 metric에 근접하거나 초과 달성

# High-level Pipeline

```
D2E recordings across all games
  ├── video frames
  ├── keyboard events
  ├── mouse raw deltas
  ├── mouse clicks / coordinates
  ├── button states
  └── active window info

Step 1. Video Encoder candidates
  D2E video
  → V-JEPA 2 based video encoder variants
  → compressed video tokens

Step 2. IDM candidates
  compressed video tokens + masked action slots
  → recover keyboard / mouse / click action labels

Step 3. Pseudo-labeling
  video-only input
  → IDM-predicted action tokens / MCAP-style events

Step 4. FDM candidates
  past video tokens + past action tokens
  → next action token / next action bin prediction

Step 5. Offline Evaluation
  D2E-style action metrics
  GT-label FDM vs pseudo-label FDM
  per-game / per-category / held-out-game generalization
  scale trend analysis
```