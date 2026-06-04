# Literature Survey: FDM-1 Public Recipe
link: https://si.inc/posts/fdm1/

> Spec boundary: this file records public claims and plausible missing details. It is not the canonical local reproduction spec. Use `docs/reproduction_spec/CANONICAL_SPEC.md` for required metrics, baselines, and gates.
> Reproduction target note: the FDM component is closed source; local FDM comparisons should therefore report a FDM-1 target-gap analysis rather than treating simple baselines as the final objective.


# Data
* For IDM pretraining:
  * 40k hours of contractor-labeled screen recordings

* For FDM pretraining:
  * screen recordings from / within the 11M-hour video corpus
  * actions are pseudo-labeled by the trained IDM
  * FDM training also uses transcription tokens for downstream instruction tuning and language grounding
  * reported transcript scale: ~1.25T transcript tokens

# Models
## 전체 구조
```text
raw screen video
   ↓
Video Encoder
   ↓ compressed video tokens / embeddings

1) IDM:
   compressed video tokens + masked action tokens
   → missing action labels 예측
   → internet-scale video에 pseudo action labels 생성

2) FDM:
   past compressed video tokens + past action tokens
   → next action 예측
   → 실제 computer action model
```

주의: Video Encoder가 action token까지 함께 압축한다고 보기는 어렵다.
더 안전한 해석은 다음과 같다.

```text
Video Encoder:
  raw video frames → compressed video/frame tokens

IDM / FDM:
  compressed video/frame tokens + action/mask tokens → action prediction
```

## Video Encoder
* 역할:
  * 30 FPS screen recording을 적은 수의 token으로 압축
  * 화면 속 text, cursor movement, UI state 등 computer-use에 중요한 정보를 가능한 한 보존
* Input:
  * raw 30 FPS screen video frames
* Output:
  * compressed video tokens or embeddings
* Training objective:
  * masked compression objective
  * self-supervised prediction task를 통해 information-dense embeddings를 만들도록 학습
  * V-JEPA와 비슷한 철학이지만, 포스트는 “exactly V-JEPA”라고 말하지 않음
* Reported compression:
  * 32k tokens → 3 min 30 sec
  * 200k tokens → 20 min
  * 1M tokens → 1 hour 40 min
* Evaluation metric:
  * Primary:
    * random text transcription accuracy
    * tokens/frame or seconds/token compression ratio
    * downstream frozen-encoder action prediction NLL / accuracy
  * Secondary:
    * frame reconstruction loss or perceptual quality
    * inverse dynamics probe accuracy
    * latency / throughput
* 미공개:
  * encoder backbone: ViT? ConvNet? Transformer? hybrid?
  * spatial patch size
  * temporal stride / frame grouping
  * adaptive token allocation 방식
  * token compression algorithm
  * latent token dimensionality
  * positional encoding
  * masked compression objective의 정확한 target
  * mask ratio / mask span / temporal masking schedule
  * reconstruction / prediction target: pixels? latent features? text? future frames?
  * encoder를 IDM/FDM 학습 때 freeze하는지, finetune하는지
  * training context length
  * optimizer, LR schedule, batch size, compute budget

## Tokenization
### Post-confirmed
#### IDM special token
```text
MASK_ACTION
```
* IDM masked diffusion inference에서 사용
* action slot을 가린 뒤, IDM이 각 masked position의 log probability를 예측

#### Keyboard
```text
KEY_DOWN_<physical_key>
KEY_UP_<physical_key>
```
* key press와 key release를 각각 개별 token으로 tokenize

#### Scroll
```text
SCROLL_<event>
```
* 포스트는 scroll event를 개별 token으로 tokenize한다고만 설명
* scroll magnitude/direction/binning 방식은 미공개

#### Mouse movement delta
포스트에서 확실히 말한 것:
```text
mouse delta per frame
→ split into X and Y components
→ normalize X by screen width, Y by screen height
→ each component placed into one of 49 exponentially-sized bins
```

구현 방식은 미공개이므로 두 가지 option이 가능하다.
Option 1: compound token
```text
MOUSE_MOVE_BIN_<xbin>_<ybin>  # 49 x 49 = 2401 tokens
```

Option 2: separate axis tokens
```text
MOUSE_DX_BIN_<i>              # 49 tokens
MOUSE_DY_BIN_<j>              # 49 tokens
```

### Reproduction-assumed tokens
아래는 computer-use model 구현상 필요하거나 유용하지만, 포스트에서 명시적으로 공개되지는 않은 token들이다.

#### No-op
```text
NO_ACTION
```
* frame interval 안에 action이 없거나, fixed K action slots를 padding할 때 사용
* 포스트의 self-driving eval에서는 “no action” choice가 등장하지만, 일반 FDM action vocab에 `NO_ACTION`이 어떻게 들어가는지는 미공개

#### Mouse buttons
```text
MOUSE_LEFT_DOWN
MOUSE_LEFT_UP
MOUSE_RIGHT_DOWN
MOUSE_RIGHT_UP
MOUSE_MIDDLE_DOWN
MOUSE_MIDDLE_UP
```
* 실제 computer control에는 필요할 가능성이 높음
* 하지만 포스트는 mouse button down/up token을 직접 설명하지 않음
* click 관련 정보는 “next click position” auxiliary target으로만 언급됨

#### Scroll magnitude bins, optional
```text
SCROLL_DY_BIN_<k>
SCROLL_DX_BIN_<k>
```
* 포스트-confirmed는 아님
* scroll delta가 continuous value로 수집되는 환경이라면 reproduction에서 선택 가능
* 더 보수적인 기본값은 `SCROLL_<event>` 또는 `SCROLL_DIRECTION_MAGNITUDE_BIN_<k>`

### Auxiliary target: next click position
```text
NEXT_CLICK_POSITION_BIN_<x>_<y>
```
이것은 action token vocab에 반드시 들어가는 token이라기보다, mouse movement prediction에 붙는 auxiliary prediction target으로 보는 것이 안전하다.
Recommended interpretation:
```text
shared FDM hidden state
   ├── action head
   │     └── predicts next action token
   │         e.g. MOUSE_MOVE_BIN_<dxbin>_<dybin>
   │
   └── auxiliary click-position head
         └── predicts next click position
             e.g. NEXT_CLICK_POSITION_BIN_<x>_<y>
```

Training loss example:
```text
L_total = L_next_action + λ_click * L_next_click_position
```

의미:
* `MOUSE_MOVE_BIN_<xbin>_<ybin>`:
  * 지금 실행할 mouse delta action
* `NEXT_CLICK_POSITION_BIN_<x>_<y>`:
  * 현재 cursor trajectory가 향하는 다음 click target 위치
  * trajectory 품질을 높이기 위한 보조 학습 신호

미공개:
* click position bin 개수
* screen-relative coordinate인지 absolute coordinate인지
* x/y separate head인지 2D grid classification인지
* click-position loss weight
* mouse button event와 어떻게 결합되는지

### Tokenization 미공개 사항

* exact keyboard key set
* physical key 기준인지 character 기준인지
* modifier handling: Shift / Cmd / Ctrl / Alt
* key repeat 처리
* multiple events in one frame interval 처리
* event ordering within frame interval
* no-op 처리
* mouse movement bin boundary formula
* 49 bins가 signed bins인지, zero bin을 어떻게 처리하는지
* X/Y separate token인지 compound token인지
* mouse button event token 존재 여부
* click position auxiliary head의 bin 개수와 loss
* scroll event의 direction/magnitude 표현
* cursor absolute position을 별도 state로 넣는지 여부

## IDM
* 역할:
  * action label이 없는 video에 pseudo-label 생성
  * internet-scale screen recordings를 FDM 학습용 action-labeled data로 변환
* Input:
  * 전체 video frames를 Video Encoder에 통과시킨 compressed frame/video tokens
  * action positions에 들어가는 masked action tokens
* Input sequence, conceptual form:
```text
Frame_t | MASK_ACTION_1 | MASK_ACTION_2 | ... | MASK_ACTION_K | Frame_{t+1} | ...
```

주의:
* 포스트는 “frames interleaved with mask tokens”라고만 설명한다.
* frame 사이에 mask slot을 몇 개 넣는지, variable-length action sequence를 어떻게 다루는지는 미공개다.
* reproduction에서는 fixed K action slots + `NO_ACTION` padding을 추천한다.

Recommended reproduction design:
```text
For each frame interval [t, t+1):

1. Aggregate mouse delta over the frame interval.
2. Collect discrete events:
   - KEY_DOWN
   - KEY_UP
   - SCROLL
   - MOUSE_BUTTON_DOWN/UP
3. Sort events by timestamp.
4. Serialize them into up to K action slots.
5. Pad remaining slots with NO_ACTION.
6. During IDM inference, replace all K slots with MASK_ACTION.
```

Example:
```text
Frame_t
  MASK_ACTION
  MASK_ACTION
  MASK_ACTION
  MASK_ACTION
  MASK_ACTION
  MASK_ACTION
Frame_{t+1}
```

IDM prediction:
```text
Frame_t
  MOUSE_MOVE_BIN_31_24
  KEY_DOWN_SHIFT
  KEY_DOWN_1
  KEY_UP_1
  KEY_UP_SHIFT
  NO_ACTION
Frame_{t+1}
```

* Output:
  * each masked action position의 action token log probabilities
* Architecture:
  * Video Encoder 위에 올라간 non-causal masked diffusion action model
  * frames 전체에 condition해서 masked action tokens를 예측
* Training objective:
  * masked diffusion objective
  * 가려진 action token 값을 복원
* Inference:
  * 16-step noise schedule
  * 각 masked position의 log probability 예측
  * confidence 높은 top-k predictions를 먼저 unmask
  * 전체 sequence가 labeled될 때까지 반복
* Data:
  * 40k hours contractor-labeled screen recordings
* Evaluation metric:
  * Offline held-out labeled data:
    * masked action NLL / cross entropy
    * top-1 / top-k action accuracy
    * per-action-type accuracy:
      * keyboard
      * mouse movement
      * scroll
      * mouse button
      * no-op
    * mouse delta dequantized error:
      * normalized L1 / L2
      * pixel error
      * angular error / direction accuracy
    * click position error:
      * normalized distance
      * pixel distance
      * success within radius r
    * sequence-level edit distance for sparse events
    * calibration:
      * confidence vs correctness
      * ECE
  * Labeler usefulness:
    * train same FDM on GT labels vs IDM pseudo-labels
    * compare downstream rollout score
    * compare scaling trend under fixed compute/data budget

* 미공개:
  * IDM model size
  * transformer layer 수, hidden size, attention heads
  * video/action token fusion 방식
  * full self-attention인지 cross-attention인지
  * train-time masking/noise schedule
  * inference 16-step schedule의 세부값
  * top-k unmasking에서 k schedule
  * confidence score 정의
  * loss weighting by action type
  * class imbalance 처리
  * context length
  * fixed K action slots를 썼는지 variable-length sequence를 썼는지
  * pseudo-label filtering threshold
  * pseudo-label confidence calibration

## FDM
* 역할:
  * 실제 computer action model
  * prior frames and actions를 보고 next action을 예측
* Input:
  * prior compressed video/frame tokens
  * prior action tokens
  * training 중 일부 transcript tokens
* Output:
  * next action token
  * optionally, auxiliary next click position prediction
* Architecture:
  * video tokens와 action tokens를 interleaved sequence로 받아 autoregressive하게 next action을 예측하는 model
  * 포스트는 “interleaved frame and action data”라고 설명
  * 구체적인 transformer architecture는 미공개
* Training objective:
  * next action prediction
  * likely autoregressive cross-entropy over action tokens
  * if click-position auxiliary head is used:

```text
L_total = L_next_action + λ_click * L_next_click_position + optional transcript/language losses
```

* Data:
  * IDM-labeled internet-scale videos
  * downstream instruction tuning과 language grounding을 위한 transcript tokens
  * transcript scale: ~1.25T tokens
* Evaluation metric:
  * Offline:
    * next-action NLL / perplexity
    * top-1 / top-k action accuracy
    * per-type accuracy:
      * key
      * mouse movement
      * scroll
      * click / mouse button
      * no-op
    * mouse delta dequantized L1 / L2 pixel error
    * click position error
    * long-context degradation curve
    * action timing accuracy
  * Online rollout:
    * task success rate
    * normalized score per task
    * time-to-completion
    * number of actions
    * invalid action rate
    * recovery after mistake
    * latency sensitivity
  * Post-aligned online task categories:
    * Typing Test
    * Verbal Memory
    * Symbolic Memory
    * Target Accuracy
    * UI Manipulation
    * 3D Manipulation / CAD
    * optional: self-driving-style keypress control after finetuning

* 미공개:
  * FDM model architecture and size
  * context length actually used during training
  * action/video/transcript token interleaving format
  * transcript tokenization 방식
  * transcript loss weight
  * action loss와 transcript loss의 mixture ratio
  * pseudo-label noise handling
  * GT contractor data와 pseudo-label data를 섞는지 여부
  * curriculum / sequence length schedule
  * sampling strategy during inference
  * latency constraints during training/inference
  * optimizer, LR schedule, batch size, total compute
  * online rollout environment details
  * eval task definitions and score functions
