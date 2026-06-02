# Key Reproduction Decisions

## Data

* exact D2E revision
* exact list of games
* per-game categories
* train/val/test split
* held-out-game split
* data scale split
* whether to include menu/loading/inactive segments
* whether to use audio
* whether to use active window metadata
* whether to train one generalist model or also per-game specialists

## Tokenization

* 50ms vs 33ms timestep
* K action slots per bin
* mouse compound token vs separate dx/dy tokens
* mouse bin boundary formula
* scroll representation
* click-position grid size
* key/button state auxiliary targets
* event overflow handling

## Video Encoder

* V-JEPA 2 checkpoint
* frozen vs LoRA/adapters vs last-block finetune
* masked video domain adaptation objective
* number of video tokens per bin
* temporal compressor architecture
* whether to finetune encoder during IDM/FDM training
* feature caching vs on-the-fly feature extraction

## IDM

* non-causal attention window
* future offset τ
* masked diffusion schedule
* number of unmasking steps
* top-k schedule
* confidence filtering
* pseudo-label calibration
* all-games model vs per-game specialist model

## FDM

* context length
* action loss weights
* pseudo-label filtering
* GT/pseudo mixture ratio
* sampling strategy for free-running-on-logged-video
* whether to use game ID embedding
* whether to add action chunk prediction
* model size sweep