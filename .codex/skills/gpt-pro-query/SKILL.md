---
name: gpt-pro-query
description: Use in this repo when Codex needs to ask ChatGPT Pro/Extended through Playwright for FDM-1/D2E phase literature review, implementation or experiment critique, theoretical plausibility review, result/phase-exit review, or failure-recovery review; save prompt, response, metadata, and integration artifacts under notes/investigations/gpt_pro/.
---

# GPT-Pro Query

Use this as the repo-local external reviewer path. Do not silently substitute a local CLI model alias or `codex exec` invocation
for a Pro query or ordinary web search for GPT-Pro unless the user explicitly says so for the current turn.

## Core Rules

- **Use real ChatGPT Pro Extended:** use the browser-accessed Pro/Extended session through Playwright; do not silently substitute local models, `codex exec`, ordinary web search, or non-Pro modes.
- **Pro has no local context:** summarize the repo evidence needed for judgment; Pro cannot see local code, logs, checkpoints, git history, or private metrics unless you include a distilled version.
- **State the agent hypothesis first:** ask Pro to critique a candidate interpretation, plan, or success criterion; do not ask “what should we do?” from a blank slate.
- **One focused question per turn:** keep each query centered on one bottleneck. Use multi-turn follow-up inside the same thread for the same line of inquiry; use a new thread for unrelated concerns.
- **Protect private state:** never send secrets, tokens, `.env` values, private credentials, raw cluster tokens, or long raw logs/config dumps.
- **Persist artifacts:** save the exact prompt before submission; save the response, metadata, and integration note after completion.
- **Evidence-after-execution docs:** never update `ROADMAP.md` or `DECISIONS.md` from Pro advice alone.

## Common Rules

### Thread management

Treat the ChatGPT conversation id (`/c/<id>`) in URL as the durable thread key for one topic. Continue an existing thread only when the topic, metrics, branch, and anchoring assumptions are still the same. Start a fresh thread when the anchor changes, the prior context is stale, or the next question is a different bottleneck. Follow-ups must begin with a stance label toward the previous answer: `accept`, `partial-accept`, or `reject`.

### What to attach

Attach distilled context, not dumps:

- phase objective and relevant spec constraints;
- 3-5 decisive facts, metrics, or observations;
- experiment/history narrative: what was tried, what failed, what worked, what was learned;
- architectural/training/evaluation constraints that bound the solution space;
- the candidate hypothesis, implementation path, or next experiment Pro should critique.

Omit secrets, raw csv, exhaustive tables, full YAML configs, long logs.

### What to ask for

Ask Pro for the leverage Codex cannot reliably get from local inspection alone:

- hidden assumptions, confounds, or counterexamples;
- weakest sufficient condition or weakest plausible success mechanism;
- cheapest falsifier or cheap success probe;
- theoretical plausibility of an objective, architecture, or metric;
- phase-exit judgment: whether evidence is strong enough to proceed.

Do not use Pro for first-pass local log diagnosis, broad “design the whole system” requests, generic literature dumps, expensive experiment matrices, or equations already established in the repo.

## Query types

Use one label in `metadata.json` and in the prompt preamble.

- `pre-phase-literature-review` — Use before starting a ROADMAP phase or major phase story when the chosen method may be stale, incomplete, or too optimistic. Ask Pro to identify the most relevant modern methods, missing papers, and assumptions to verify before implementation. The output should feed curated `docs/literature_survey/` updates and a staged `notes/plans/phase-*` plan, not direct execution.
- `implementation-direction-critique` — Use after the agent has a concrete implementation path but before substantial code/training investment. Ask whether the proposed architecture, objective, data flow, tokenization, sampler, or harness design has hidden blockers or simpler alternatives under this repo's constraints.
- `experiment-design-critique` — Use before running costly MLXP jobs, ablations, scaling curves, or pseudo-label sweeps. Ask whether the proposed comparison isolates the intended variable, whether cheaper falsifiers exist, and which metrics or controls are necessary for an interpretable result.
- `result-phase-exit-review` — Use after implementation or experiments produce evidence and before declaring a phase complete or moving to the next phase. Ask whether the observed metrics, failures, artifacts, and controls are sufficient for phase exit, or what minimal additional evidence is required.
- `failure-recovery-review` — Use when a branch fails, stalls, or contradicts the spec. Ask for the cheapest falsifier of the current diagnosis, the weakest plausible success mechanism, and the cheapest success probe; do not ask only whether to abandon the branch.
- `theoretical-plausibility-review` — Use when the concern is conceptual rather than operational: e.g., whether an IDM/FDM objective matches the causal structure, whether a diffusion formulation is well-posed, whether a representation probe can support the intended claim, or whether a metric actually measures the desired capability.

## Artifact contract

Use one directory per ChatGPT thread and one subdirectory per turn. The thread directory is the durable artifact for one line of inquiry.

```text
notes/investigations/gpt_pro/
  phase-1-video-encoder/
    20260605-gameplay-domain-adaptation/
      metadata.json
      anchor.md
      synthesis.md
      turns/
        001-pre-phase-literature-review/
          prompt.md
          response.md
          integration.md
        002-followup-partial-accept/
          prompt.md
          response.md
          integration.md
```

Thread-level files:

- `metadata.json` — machine-readable thread registry: phase, topic, conversation id, ChatGPT URL, model mode, related docs, turn list, and status.
- `anchor.md` — the stable contract for reusing the thread: topic, phase objective, key assumptions, metric definitions, branch/run context, and stale-thread conditions.
- `synthesis.md` — rolling agent synthesis across turns: accepted claims, rejected claims, unresolved questions, primary-source checks, and next action.

Turn-level files:

- `turns/<nnn>-<query-type-or-followup>/prompt.md` — exact submitted prompt for that turn.
- `turns/<nnn>-<query-type-or-followup>/response.md` — full Pro response for that turn, preserved as the answer of record.
- `turns/<nnn>-<query-type-or-followup>/integration.md` — agent verdict and integration for that turn.

`metadata.json` should include at least:

```json
{
  "date_created": "YYYY-MM-DD",
  "date_updated": "YYYY-MM-DD",
  "phase": "phase-1-video-encoder",
  "topic": "gameplay domain adaptation",
  "model_mode": "Extended Pro",
  "chatgpt_url": "",
  "conversation_id": "",
  "anchor_status": "active|stale|retired",
  "related_docs": [],
  "turns": [
    {
      "turn": 1,
      "query_type": "pre-phase-literature-review",
      "stance": "initial",
      "path": "turns/001-pre-phase-literature-review",
      "status": "prompt_saved|submitted|response_saved|integrated"
    }
  ]
}
```

Thread reuse rules:

- Continue the same thread only if `anchor.md` still matches the current topic, metrics, branch/run context, and assumptions.
- Add a new `turns/<nnn>-.../` directory for each follow-up instead of appending to prior prompt/response files.
- Update `synthesis.md` after every integrated turn so a later agent can understand the current judgment without rereading every response.
- Mark `anchor_status: "stale"` or `"retired"` rather than reusing an old thread for a materially different question.

## Prompt shape

Write natural prose, not a long structured form. Include:

1. Project setup and phase objective in 2-4 sentences.
2. The 3-5 local facts/evidence items Pro needs.
3. The agent's current hypothesis or candidate plan.
4. One focused question asking for critique, missing assumptions, blockers, falsifiers, or success conditions.

Omit full YAML configs, raw tables, long code blocks, secrets, and exhaustive logs.

## Browser procedure

Also follow the installed `playwright` skill guardrails.

1. Ensure Playwright can use the authenticated Chrome profile:

   ```bash
   command -v npx >/dev/null 2>&1
   export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
   export PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"
   export PW_PROFILE="$HOME/.pw-profiles/codex-chrome"
   ```

2. Open ChatGPT with the persistent profile:

   ```bash
   "$PWCLI" open https://chatgpt.com/ --browser=chrome --profile="$PW_PROFILE" --headed
   "$PWCLI" snapshot
   ```

3. Verify the UI shows the authenticated Pro account. If it shows a login gate, stop and report an auth blocker.

4. Ensure temporary chat is off, because the conversation id must be recoverable.

5. Select `Pro • Extended` / `Extended Pro` from the model menu. Snapshot after selection.

6. Paste or fill the saved turn-level `turns/<nnn>-.../prompt.md` content into the composer and send it. Do not send unsaved prompt text.

7. Wait until generation is complete. Treat `Stop answering` or `data-testid="stop-button"` as still generating; wait until the normal send control returns.

8. Save the full visible answer to the same turn's `response.md`. Prefer the ChatGPT copy button if available; otherwise use a fresh snapshot or DOM extraction. Preserve enough text to reconstruct the answer, not only a summary.

9. Record the current URL and conversation id (`/c/<id>`) in thread-level `metadata.json`, and add/update the current turn entry.

10. Write the same turn's `integration.md` with:
    - verdict: accept / partial-accept / reject;
    - newly identified papers or methods to verify through primary sources;
    - conflicts with current spec or assumptions;
    - adopted, deferred, and rejected recommendations;
    - next implementation/experiment implication. Then update thread-level `synthesis.md`.

11. If the answer cites papers or claims current method status, verify against primary sources before updating `docs/literature_survey/`. The literature file must be curated; never paste the Pro answer verbatim as survey text.
