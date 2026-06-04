# Reproduction docs authority

이 디렉토리는 FDM-1-with-D2E research reproduction의 계획/스펙 문서를 담는다.

- `CANONICAL_SPEC.md` is the primary research/reproduction source of truth.
- `OPERATIONAL_RULES.md` is the execution/logistics source of truth.
- `ROADMAP.md` tracks phase-by-phase reproduction progress as an implementation/evaluation checklist.
- `DECISIONS.md` records final reproduction decisions as they are made.
- `spec/` contains component/protocol details only: data/actions, video encoder, IDM, FDM, and evaluation. Training progress belongs in `ROADMAP.md`; final choices belong in `DECISIONS.md`.
- During implementation, treat these docs as authoritative. If a user explicitly asks to revise the spec, edit the docs and repair inconsistencies instead of preserving stale text.
