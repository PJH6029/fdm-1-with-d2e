# Literature Survey: Video Encoder Candidates for FDM-1 with D2E

Status: draft survey as of 2026-06-04.  
Scope: pretrained or reusable visual/video encoders relevant to D2E gameplay/screen recordings.

## Executive conclusion

The concern is justified: the strongest public video encoders are mostly trained on natural/web video, action-recognition datasets, video-text corpora, or physical-world/robot data. I did not find evidence that V-JEPA 2, VideoPrism, InternVideo2, or VideoMAE v2 are explicitly pretrained on desktop/gameplay screen recordings as a primary domain. Therefore, for D2E reproduction, a frozen pretrained video encoder should be treated as an initialization and diagnostic baseline, not as a source of sufficient computer/gameplay domain knowledge.

The key reproduction risk is not only selecting the right temporal tokens. The video encoder may need to learn the visual grammar of gameplay recordings: HUDs, crosshairs, cursors, UI menus, tiny text/icons, camera motion, inventory state, health/ammo bars, minimaps, and screen-space affordances. D2E-scale domain adaptation of the encoder is likely central to a serious FDM-1 reproduction.

Recommended candidate strategy:

1. **Keep V-JEPA 2 / V-JEPA 2.1 as the main starting point** because FDM-1 publicly references a V-JEPA-like masked/predictive video representation and V-JEPA 2 is a strong self-supervised video/world-model encoder.
2. **Run a short bakeoff against VideoPrism and VideoMAE v2 or InternVideo2** using D2E frozen action probes and Tiny-IDM/Tiny-FDM transfer before committing to Base runs.
3. **Plan for D2E gameplay-domain adaptation** unless probes show unexpectedly strong held-out-game performance from frozen features.
4. **Use UI/screen-specialized models as evidence and possible auxiliary modules**, not as direct replacements for a temporal gameplay encoder.

## What D2E needs from a video encoder

A D2E FDM-1-style encoder must preserve information that differs from ordinary natural video understanding:

- precise screen-space layout and small objects;
- UI text, icons, menus, inventory bars, health/ammo/minimap HUDs;
- cursor/crosshair location and movement cues;
- game-state changes under rapid camera motion;
- low-motion states where a tiny UI change matters;
- long-context state such as location, inventory, objective, menu navigation, or repeated interaction history;
- action-relevant affordances rather than only semantic scene/action class.

This favors an evaluation strategy based on game-action probes, held-out-game generalization, and long-context compression rather than generic video classification alone.

## Candidate families

### V-JEPA / V-JEPA 2 / V-JEPA 2.1

Evidence:

- The original V-JEPA repository says V-JEPA models are trained by passively watching video pixels from **VideoMix2M** and are commonly used as a frozen backbone with a lightweight task-specific probe.
- V-JEPA 2 reports pretraining on **over 1 million hours of internet video** plus images, then optional action-conditioned post-training on **less than 62 hours of DROID robot videos** for robot planning.
- V-JEPA 2 reports strong motion/action benchmark results such as Something-Something v2 and Epic-Kitchens-100, and VQA after LLM alignment.

Strengths for D2E:

- Self-supervised latent prediction is philosophically close to FDM-1's public description.
- It is a good starting point for motion/state representation and long-horizon world-model-style work.
- Frozen-probe usage matches the way we can evaluate representation quality cheaply.

Main concern:

- Public sources emphasize internet/natural video, images, and robot physical-world post-training; they do not establish computer-screen/gameplay domain coverage.
- A physical-world representation may underweight UI text, HUD pixels, cursor/crosshair affordances, and discrete game state.

Recommendation:

- Use V-JEPA 2/2.1 as the **primary initialization**, not as an assumed-sufficient frozen encoder.
- Require D2E gameplay probes before trusting frozen features.
- Prioritize adapter/LoRA/last-block or JEPA-style D2E masked-latent adaptation if frozen probes are weak.

Sources:

- V-JEPA GitHub: <https://github.com/facebookresearch/jepa>
- V-JEPA 2 paper: <https://arxiv.org/abs/2506.09985>
- V-JEPA 2.1 paper: <https://arxiv.org/abs/2603.14482>

### VideoPrism

Evidence:

- VideoPrism is a general-purpose video encoder for classification, localization, retrieval, captioning, and question answering.
- The official repository states it was pretrained on a large hybrid corpus: **1B image-text pairs**, **36M high-quality video-text pairs**, and **582M noisy/machine-text video clips**.
- Google reports a single frozen VideoPrism model achieving state-of-the-art results on many public video understanding benchmarks.

Strengths for D2E:

- Strong frozen general-purpose video representation.
- Large and diverse web-video pretraining may include some screen/game material incidentally.
- Good alternative to V-JEPA for a frozen-feature bakeoff.

Main concern:

- It is optimized for broad video understanding and video-language tasks, not necessarily control-relevant screen-state preservation.
- Public training descriptions do not indicate targeted desktop/gameplay recording pretraining.

Recommendation:

- Include as the strongest **general frozen video encoder challenger** if weights/inference are operationally usable.
- Compare against V-JEPA using the same D2E action probes and Tiny-IDM/Tiny-FDM transfer.

Sources:

- VideoPrism GitHub: <https://github.com/google-deepmind/videoprism>
- Google Research blog: <https://research.google/blog/videoprism-a-foundational-visual-encoder-for-video-understanding/>
- VideoPrism paper: <https://arxiv.org/abs/2402.13217>

### InternVideo2

Evidence:

- InternVideo2 scales video foundation models up to 6B parameters and unifies masked video modeling, cross-modal contrastive learning, and next-token prediction.
- The paper emphasizes spatiotemporal consistency and reports strong performance across video/audio tasks and long-video understanding benchmarks.

Strengths for D2E:

- Strong general video and long-video understanding candidate.
- Cross-modal/video-language training may help with semantic state, menus, and narrated videos if the representation is accessible.

Main concern:

- It is large and potentially operationally heavy for feature caching and D2E-scale sweeps.
- No clear evidence of targeted computer/gameplay screen recording pretraining.

Recommendation:

- Treat as an optional high-capacity challenger if engineering cost is acceptable.
- Use for probes first; do not make it the default until throughput/cache constraints are measured.

Source:

- InternVideo2 paper: <https://arxiv.org/abs/2403.15377>

### VideoMAE v2

Evidence:

- VideoMAE v2 is a scalable masked-autoencoder video pretraining approach.
- It reports billion-parameter video ViT training and strong Kinetics/Something-Something results.

Strengths for D2E:

- Masked reconstruction-style pretraining can preserve low-level visual detail better than purely semantic video-language encoders.
- Potentially useful when UI/HUD/cursor details matter.

Main concern:

- Main public results are standard action-recognition datasets, not computer/game screen recordings.
- It may still learn natural-video/action-recognition biases unless adapted.

Recommendation:

- Include as a practical MAE-style baseline if V-JEPA/VideoPrism probes fail on UI/detail-heavy segments.
- More likely useful after D2E domain adaptation than as a purely frozen encoder.

Source:

- VideoMAE v2 paper: <https://arxiv.org/abs/2303.16727>

### Game/domain-specific precedents: VPT, MineCLIP, Genie

These are not drop-in general D2E video encoders, but they strongly support the claim that gameplay video needs domain-specific representation learning.

#### OpenAI VPT

Evidence:

- VPT trained a Minecraft agent from a large unlabeled dataset of human Minecraft play plus a small labeled contractor dataset.
- The pipeline uses an IDM to label online Minecraft videos and then behavioral cloning to learn actions.
- The OpenAI post emphasizes native keyboard/mouse control and general computer-using-agent relevance.

Relevance:

- VPT is the closest public methodological precedent for FDM-1-style IDM → pseudo-label → action model in a game domain.
- It supports the idea that game-specific video/action data is necessary; generic video representation alone is not enough.

Source:

- OpenAI VPT post: <https://openai.com/index/vpt/>
- VPT paper: <https://arxiv.org/abs/2206.11795>

#### MineCLIP / MineDojo

Evidence:

- MineCLIP is trained on a MineDojo video dataset of Minecraft YouTube videos with transcripts and is used as a video-language reward/model component for Minecraft agents.
- MineDojo reports a large Minecraft-specific knowledge base of videos, wiki pages, and forum discussions.

Relevance:

- Useful evidence that game-specific video-language pretraining helps, but Minecraft-specific representations are unlikely to transfer cleanly to all D2E games.

Sources:

- MineCLIP GitHub: <https://github.com/MineDojo/MineCLIP>
- MineDojo project: <https://minedojo.org/index.html>
- MineDojo paper: <https://arxiv.org/abs/2206.08853>

#### Genie

Evidence:

- Genie is a generative interactive environment trained from unlabeled internet videos, with a spatiotemporal tokenizer, dynamics model, and latent action model.
- It can create action-controllable virtual worlds without ground-truth action labels.

Relevance:

- It is a world-model/generative environment, not a drop-in encoder for D2E IDM/FDM.
- It supports the idea that action-controllable/game-like visual domains require learning latent action/state structure from video, not just semantic recognition.

Source:

- Genie publication: <https://deepmind.google/research/publications/60474/>
- Genie paper: <https://arxiv.org/abs/2402.15391>

### UI/screen-specific models: ScreenAI, OmniParser, ShowUI

These are mostly image/screenshot/UI models rather than temporal video encoders, but they are important evidence for the domain gap.

Evidence:

- ScreenAI is explicitly designed for UI and infographic understanding, with screen annotation tasks for UI element type/location/description.
- OmniParser argues that general multimodal models are limited as GUI agents without robust screen parsing of interactable regions and semantics.
- ShowUI introduces UI-guided visual token selection and interleaved vision-language-action streaming for GUI agents.

Relevance to D2E:

- D2E includes UI-heavy and menu-heavy gameplay. Generic video encoders may not preserve the tiny text/icon/layout details needed for control.
- These models are not direct video encoder replacements, but they suggest adding screen/UI auxiliary objectives or per-frame UI parsing probes.

Sources:

- ScreenAI blog: <https://research.google/blog/screenai-a-visual-language-model-for-ui-and-visually-situated-language-understanding/>
- ScreenAI paper: <https://arxiv.org/abs/2402.04615>
- OmniParser paper: <https://arxiv.org/abs/2408.00203>
- ShowUI paper: <https://arxiv.org/abs/2411.17465>

## Overall assessment

| Candidate | Why consider it | Main D2E risk | Recommended role |
| --- | --- | --- | --- |
| V-JEPA 2 / 2.1 | FDM-1-adjacent JEPA style; strong self-supervised video/world representation | likely natural/physical-world bias; no clear screen/game pretraining | primary initialization + adaptation target |
| VideoPrism | strong frozen general-purpose video encoder over broad web data | semantic/video-language bias; no targeted control/screen domain | frozen challenger in probe bakeoff |
| InternVideo2 | high-capacity multimodal/long-video understanding | heavy; no clear gameplay-screen domain | optional high-capacity challenger |
| VideoMAE v2 | masked video modeling may preserve details | action-recognition/natural-video bias | MAE-style baseline/adaptation candidate |
| VPT | public game-video action-learning precedent | Minecraft-specific; not a reusable general encoder | methodological evidence |
| MineCLIP | Minecraft-specific video-language game representation | domain-specific to Minecraft | evidence/optional auxiliary comparison only |
| Genie | unsupervised interactive video-world model | not a drop-in encoder; generative model | conceptual evidence for latent action/state learning |
| ScreenAI/OmniParser/ShowUI | explicit UI/screen domain knowledge | mostly static screenshot/UI, not gameplay video | evidence + possible auxiliary probes/modules |

## Recommendation for this reproduction

The current plan should assume **frozen generic video encoders are insufficient until proven otherwise**. The practical path should be:

1. **Probe first:** compare V-JEPA 2/2.1, VideoPrism, and one MAE/action-recognition family encoder on D2E action probes.
2. **Adapt second:** if frozen features are weak, run D2E self-supervised gameplay adaptation before expensive IDM/FDM sweeps.
3. **Evaluate by downstream action utility:** promote encoders only if Tiny-IDM/Tiny-FDM metrics improve on held-out games.
4. **Add screen/game auxiliary signals:** consider OCR/text, cursor/crosshair, HUD state, UI/menu segmentation, and next-click/action probes as auxiliary losses or diagnostics.
5. **Keep long-context compression central:** evaluate not only per-frame quality but whether the encoder/resampler supports long contexts without losing state.

A good D2E reproduction should therefore treat video encoder adaptation as a core research contribution, not as a minor token-selection component.
