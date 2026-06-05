# Synthesis — Phase 0 exit review

Status: GPT-Pro phase-exit review completed and integrated.

Accepted claims:
- Phase 0 is substantively strong on data discovery, manifest/split/scale generation, 50ms action distribution, local evaluator fixture round-trip, and pinned official D2E evaluator availability.
- Official `evaluate.py` runtime-library recovery is an image reproducibility issue; bake the libraries into a future official-evaluation image.
- One final Phase 0 blocker remains unless already satisfied: official `evaluate.py` must score a writer-produced prediction MCAP, not just the same ground-truth MCAP passed as both inputs.

Rejected/deferred claims:
- Full all-game official evaluation is deferred; one writer-produced official round-trip is the cheapest independent oracle.
- Keyboard label policy audit, full distribution sweeps, binary-reader-vs-JSON-reader agreement sweeps, and baked official-eval image are follow-ups, not immediate Phase 0 blockers after the writer-produced official round-trip.

Next action:
- Add/execute a follow-up Ultragoal story for a real-recording writer-produced MCAP official-evaluator round-trip with file provenance/hash evidence.
