"""FDM-1 with D2E reproduction package bootstrap.

This package is intentionally contract-first during Phase 0. The G001 story only
creates importable package/config/schema surfaces; reader, binning,
tokenization, and evaluator behavior are implemented by later Ultragoal stories.
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "BOOTSTRAP_STORY_ID",
    "BOOTSTRAP_PHASE",
    "OFFLINE_DEFAULT_TEST_CONTRACT",
    "bootstrap_contract",
]

__version__ = "0.0.0"
BOOTSTRAP_STORY_ID = "G001-bootstrap-package-configs-and-schema"
BOOTSTRAP_PHASE = "phase-0-data"

OFFLINE_DEFAULT_TEST_CONTRACT = {
    "requires_live_network": False,
    "requires_hugging_face": False,
    "requires_mlxp": False,
    "requires_d2e_dataset": False,
}


def bootstrap_contract() -> dict[str, object]:
    """Return a copy of the Phase 0 bootstrap contract for smoke checks."""

    return {
        "story_id": BOOTSTRAP_STORY_ID,
        "phase": BOOTSTRAP_PHASE,
        "package_version": __version__,
        "default_tests": dict(OFFLINE_DEFAULT_TEST_CONTRACT),
        "status": "bootstrap_only_no_reader_tokenizer_or_evaluator_logic",
    }
