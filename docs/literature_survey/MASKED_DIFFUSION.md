# Literature Survey: Masked and Discrete Diffusion Models

Status: draft survey as of 2026-06-04.
Scope: masked diffusion, discrete diffusion language models, multimodal diffusion LMs, and discrete/action-token diffusion. This file is a literature survey only; downstream reproduction choices belong in `docs/reproduction_spec/spec/idm.md`.

## Executive summary

Masked/discrete diffusion models replace the Gaussian noising process used for images with a noising process over categorical states. The most relevant variant for token sequences is **absorbing-mask diffusion**: clean tokens are progressively replaced by a `[MASK]` state, and a denoising model predicts clean tokens from partially masked inputs.

Important recurring ideas across the literature:

- **Diffusion is not the absence of cross entropy.** Many masked diffusion objectives reduce in practice to weighted cross-entropy losses over noised/masked positions. The diffusion-specific parts are the forward corruption process, noise/timestep conditioning, schedule weighting, and iterative reverse sampler.
- **Absorbing masks connect MLMs and diffusion.** BERT-style masked language modeling is a denoising ancestor; D3PM/ARDM/DiffusionBERT/MDLM/MD4 formalize mask-based generation as discrete diffusion.
- **Parallel generation is a core advantage.** Masked diffusion can fill multiple uncertain tokens per step using confidence, entropy, or schedule-driven reveal orders instead of left-to-right decoding.
- **Schedules matter.** Modern work studies continuous-time masking, state-dependent noise, data-driven schedules, token-level rescheduling, remasking, and correction of visible wrong tokens.
- **Scaling is now credible.** Recent systems such as LLaDA-style models, block diffusion, and commercial/open diffusion LMs indicate that masked diffusion can scale beyond toy text settings, although the strongest public recipes remain less mature than autoregressive LMs.

## Terminology map

| Term | Meaning |
| --- | --- |
| Clean data `x0` | Original categorical sequence before noising. |
| Corrupted data `x_t` or `x_u` | Sequence after applying a discrete noising process at timestep/noise level. |
| Absorbing mask | A special `[MASK]` state that tokens enter during the forward process. |
| Transition matrix | Categorical noising kernel, e.g. uniform, nearest-neighbor, absorbing-mask, or state-dependent. |
| Denoiser / reverse model | Model that predicts clean tokens, score ratios, or reverse transitions from corrupted inputs. |
| Noise level / timestep | Discrete or continuous scalar controlling corruption strength. |
| Schedule | Rule mapping timestep/noise level to corruption probability and loss/reveal weighting. |
| Sampler | Iterative reverse process that converts fully or partially noised inputs into clean sequences. |
| Confidence-guided unmasking | Decoding strategy that reveals high-confidence predictions first and leaves uncertain positions masked. |
| Remasking / correction | Strategy that revisits already visible predictions rather than treating unmasked tokens as final. |

## Chronological survey

### 0. Non-diffusion ancestors: MLM, mask-predict, and MaskGIT

**BERT-style masked language modeling** established the bidirectional denoising setup: randomly mask some tokens and train a transformer to predict the originals from context. It is not a full generative diffusion model because it lacks an explicit forward Markov process, timestep/noise conditioning, and reverse sampling schedule, but it is the practical ancestor of many masked-token diffusion objectives.

**Mask-Predict** and related non-autoregressive translation methods showed that generation can proceed by iteratively filling and revising masks rather than decoding strictly left to right.

**MaskGIT** applies a bidirectional masked-token transformer to image-token generation. It starts from masked tokens, predicts all masked positions, keeps high-confidence predictions, and iteratively refines the rest. Although framed for visual token generation rather than discrete diffusion theory, its confidence-based parallel decoding strongly influenced later masked generation practice.

Source:

- MaskGIT: <https://arxiv.org/abs/2202.04200>

### 1. DDPM and discrete diffusion foundations

#### DDPM

Denoising Diffusion Probabilistic Models (DDPM) popularized the modern diffusion recipe: a fixed forward noising process, a learned reverse process, a variational/training objective, and iterative denoising from noise to data. DDPM is continuous-domain, but it defines the conceptual template later adapted to discrete states.

Source: <https://arxiv.org/abs/2006.11239>

#### Multinomial diffusion and D3PM

Argmax Flows and Multinomial Diffusion introduced diffusion-style models over categorical variables. **D3PM** generalized discrete noising with transition matrices, including uniform corruption, structured/nearest-neighbor corruption, and absorbing-state transitions. D3PM also showed that auxiliary clean-token prediction losses can improve discrete diffusion training.

Sources:

- Argmax Flows and Multinomial Diffusion: <https://arxiv.org/abs/2102.05379>
- D3PM / Structured Denoising Diffusion Models in Discrete State-Spaces: <https://arxiv.org/abs/2107.03006>

#### ARDM

Autoregressive Diffusion Models (ARDM) connect order-agnostic autoregressive generation and absorbing discrete diffusion. Instead of a fixed left-to-right factorization, ARDM learns to generate under arbitrary reveal orders, making it an important bridge between autoregressive models and mask-based diffusion.

Source: <https://arxiv.org/abs/2110.02037>

#### Continuous-time discrete denoising

Continuous-time discrete denoising formulations replace a finite hand-written diffusion chain with continuous noise levels. This makes schedules cleaner to specify and train, and it anticipates the continuous-time objectives used by later masked diffusion LMs.

Source: <https://arxiv.org/abs/2205.14987>

### 2. Early text diffusion models

#### Diffusion-LM

Diffusion-LM applies continuous diffusion to word-vector sequences and supports controllable generation through gradients in latent space. It is historically important, but it uses continuous embeddings rather than a purely categorical mask process.

Source: <https://arxiv.org/abs/2205.14217>

#### DiffuSeq and SeqDiffuSeq

DiffuSeq and SeqDiffuSeq apply diffusion to conditional sequence-to-sequence text generation. They explore how denoising objectives can be adapted to conditional generation tasks such as question generation, summarization, and translation-like settings.

Sources:

- DiffuSeq: <https://arxiv.org/abs/2210.08933>
- SeqDiffuSeq: <https://arxiv.org/abs/2212.10325>

#### DiffusionBERT

DiffusionBERT trains BERT-like models as reverse processes for absorbing-state discrete diffusion. It emphasizes timestep conditioning and token-dependent noising, making it a practical bridge from ordinary MLM to diffusion-formal masked-token generation.

Source: <https://arxiv.org/abs/2211.15029>

### 3. Modern masked discrete diffusion language modeling

#### SEDD: score entropy discrete diffusion

SEDD introduces score entropy training for discrete diffusion. Instead of only predicting clean tokens, it estimates score-like ratios for categorical distributions and reports strong language-modeling results relative to prior diffusion LMs.

Source: <https://arxiv.org/abs/2310.16834>

#### MDLM: Simple and Effective Masked Diffusion Language Models

MDLM presents masked discrete diffusion as a simple and effective language modeling approach. It clarifies that masked diffusion objectives can be expressed as weighted mixtures or integrals of masked-token cross-entropies while still retaining a diffusion process through noise-level sampling, schedule weighting, and iterative sampling.

Source: <https://arxiv.org/abs/2406.07524>

#### MD4 / Simplified and Generalized Masked Diffusion

MD4 / SGMD simplifies the masked diffusion objective and presents a generalized framework with continuous-time weighting and state-dependent masking schedules. This line is important because it makes explicit when masked CE is a diffusion objective rather than merely random-mask denoising.

Source: <https://arxiv.org/abs/2406.04329>

#### Conditional `[MASK]` discrete diffusion

Conditional masked diffusion work studies discrete diffusion under external conditioning. It helps separate noised target tokens from fixed conditioning context and is relevant to encoder-decoder or cross-attention formulations where only part of the sequence is diffused.

Source: <https://arxiv.org/abs/2411.06438>

### 4. Scaling and large diffusion LMs

#### DiffuGPT / DiffuLLaMA

DiffuGPT and DiffuLLaMA explore converting or adapting pretrained autoregressive language models into diffusion models through continual training. The broader point is that initialization from strong sequence models can reduce the cost of scaling diffusion LMs.

Source: <https://arxiv.org/abs/2410.17891>

#### LLaDA

LLaDA scales masked diffusion language modeling with a forward data masking process and reverse masked-token prediction. It shows that large diffusion LMs can be competitive on broad language tasks when trained with modern recipes and supervised adaptation.

Source: <https://arxiv.org/abs/2502.09992>

#### Block Diffusion

Block Diffusion combines autoregressive and discrete denoising diffusion ideas. It supports flexible-length generation, KV caching, parallel token sampling, and data-driven noise schedules by applying diffusion within blocks while preserving broader sequential structure.

Source: <https://arxiv.org/abs/2503.09573>

#### Mercury

Mercury is a commercial diffusion LLM family focused on high-throughput code generation. Public details are less complete than academic papers, but it is evidence that parallel diffusion decoding is being pursued at industrial scale.

Source: <https://arxiv.org/abs/2506.17298>

#### Dream 7B

Dream 7B is an open diffusion LLM that uses discrete diffusion and iterative denoising. It reports autoregressive-model initialization, context-adaptive token-level noise rescheduling, and explicit quality-speed tradeoffs.

Source: <https://arxiv.org/abs/2508.15487>

### 5. Refinement, correction, and aggressive parallel decoding

#### Partial masking / Prime

Prime argues that binary masked/unmasked states can waste computation because repeated decoding steps often see identical inputs. It introduces intermediate partial-mask states to provide smoother refinement.

Source: <https://arxiv.org/abs/2505.18495>

#### Corrective Diffusion Language Models

Corrective Diffusion Language Models analyze a weakness of standard masked diffusion: training only on masked tokens may not teach the model to identify and revise visible wrong tokens. The proposed correction-oriented training explicitly includes visible corruptions and teaches revision.

Source: <https://arxiv.org/abs/2512.15596>

#### DMax

DMax targets aggressive parallel decoding for diffusion LMs. It unifies masked and uniform denoising with on-policy training and uses soft parallel decoding that interpolates between predicted token embeddings and mask embeddings.

Source: <https://arxiv.org/abs/2604.08302>

## Multimodal and action-token diffusion

### Multimodal diffusion LMs: LLaDA-V and LaViDa

LLaDA-V and LaViDa extend masked diffusion language models into multimodal settings by connecting visual encoders to diffusion language models. They show that diffusion-token decoders can be conditioned on image/video representations rather than text-only contexts.

Sources:

- LLaDA-V: <https://arxiv.org/abs/2505.16933>
- LaViDa: <https://arxiv.org/abs/2505.16839>

### Discrete Diffusion VLA

Discrete Diffusion VLA discretizes robot action chunks and models them with discrete diffusion inside a unified transformer. It introduces action-structured discrete decoding ideas such as localized action-token classification, adaptive decoding order, and secondary remasking.

Source: <https://arxiv.org/abs/2508.20072>

### LLaDA-VLA, Unified Diffusion VLA, and MMaDA-VLA

Recent VLA papers apply masked/diffusion language-modeling ideas to robot action policies with discrete or unified multimodal token spaces. Their relevance is methodological: they explore action chunk tokenization, structured action heads, hierarchical decoding, and joint denoising across observations and actions.

Sources:

- LLaDA-VLA: <https://arxiv.org/abs/2509.06932>
- Unified Diffusion VLA: <https://arxiv.org/abs/2511.01718>
- MMaDA-VLA: <https://arxiv.org/abs/2603.25406>

## Method dimensions to compare across papers

| Dimension | Common options |
| --- | --- |
| Corruption kernel | uniform categorical, nearest-neighbor, absorbing mask, state-dependent mask |
| Time parameterization | finite timesteps, continuous time/noise level, block-local schedules |
| Prediction target | clean token `x0`, reverse transition, score ratio, corrected visible token |
| Conditioning | unconditional, prefix/seq2seq, multimodal encoder memory, interleaved context |
| Sampling | ancestral reverse chain, confidence unmasking, fixed-ratio reveal, remasking, soft/partial refinement |
| Scaling path | train from scratch, initialize from BERT/MLM, initialize from autoregressive LM, supervised adaptation |
| Failure mode | poor calibration, over-confident early reveals, inability to correct visible errors, slow many-step decoding |

## Source index

Foundational diffusion/discrete diffusion:

- DDPM: <https://arxiv.org/abs/2006.11239>
- Argmax Flows and Multinomial Diffusion: <https://arxiv.org/abs/2102.05379>
- D3PM: <https://arxiv.org/abs/2107.03006>
- ARDM: <https://arxiv.org/abs/2110.02037>
- Continuous-time discrete denoising: <https://arxiv.org/abs/2205.14987>

Masked / text diffusion:

- Diffusion-LM: <https://arxiv.org/abs/2205.14217>
- MaskGIT: <https://arxiv.org/abs/2202.04200>
- DiffuSeq: <https://arxiv.org/abs/2210.08933>
- SeqDiffuSeq: <https://arxiv.org/abs/2212.10325>
- DiffusionBERT: <https://arxiv.org/abs/2211.15029>
- SEDD: <https://arxiv.org/abs/2310.16834>
- MDLM: <https://arxiv.org/abs/2406.07524>
- MD4 / SGMD: <https://arxiv.org/abs/2406.04329>
- Conditional `[MASK]` discrete diffusion: <https://arxiv.org/abs/2411.06438>

Scaling and recent diffusion LMs:

- DiffuGPT / DiffuLLaMA: <https://arxiv.org/abs/2410.17891>
- LLaDA: <https://arxiv.org/abs/2502.09992>
- Block Diffusion: <https://arxiv.org/abs/2503.09573>
- Mercury: <https://arxiv.org/abs/2506.17298>
- Dream 7B: <https://arxiv.org/abs/2508.15487>
- Partial masking / Prime: <https://arxiv.org/abs/2505.18495>
- Corrective Diffusion LM: <https://arxiv.org/abs/2512.15596>
- DMax: <https://arxiv.org/abs/2604.08302>

Multimodal/action diffusion:

- LLaDA-V: <https://arxiv.org/abs/2505.16933>
- LaViDa: <https://arxiv.org/abs/2505.16839>
- Discrete Diffusion VLA: <https://arxiv.org/abs/2508.20072>
- LLaDA-VLA: <https://arxiv.org/abs/2509.06932>
- Unified Diffusion VLA: <https://arxiv.org/abs/2511.01718>
- MMaDA-VLA: <https://arxiv.org/abs/2603.25406>
