from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import fdm_1_with_d2e
import fdm_1_with_d2e.cluster as cluster
import fdm_1_with_d2e.data as data
import fdm_1_with_d2e.evaluation as evaluation
import fdm_1_with_d2e.harness as harness
import fdm_1_with_d2e.models as models
import fdm_1_with_d2e.pseudo_labeling as pseudo_labeling
import fdm_1_with_d2e.reporting as reporting
import fdm_1_with_d2e.tokenization as tokenization
import fdm_1_with_d2e.training as training
import fdm_1_with_d2e.video as video

REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_STORY_ID = "G001-bootstrap-package-configs-and-schema"
MANIFEST_STORY_ID = "G004-implement-manifests-and-action-distr"
EVALUATOR_STORY_ID = "G005-implement-evaluator-and-official-d2e"
SCRIPTS = [
    "build_d2e_manifest.py",
    "summarize_action_distribution.py",
    "d2e_roundtrip_check.py",
    "locate_d2e_reference.py",
]


def test_package_import_contract_is_offline_bootstrap_only() -> None:
    contract = fdm_1_with_d2e.bootstrap_contract()
    assert contract["story_id"] == "G001-bootstrap-package-configs-and-schema"
    assert contract["default_tests"] == {
        "requires_live_network": False,
        "requires_hugging_face": False,
        "requires_mlxp": False,
        "requires_d2e_dataset": False,
    }
    assert data.BOOTSTRAP_STATUS == "reader_and_binning_contract_implemented"
    assert data.MANIFEST_STATUS == "dataset_split_scale_action_distribution_manifests_implemented"
    for module in (
        cluster,
        evaluation,
        harness,
        models,
        pseudo_labeling,
        reporting,
        tokenization,
        training,
        video,
    ):
        assert module.BOOTSTRAP_STATUS == "placeholder_contract_only"


def test_cli_wrappers_emit_placeholder_contracts_without_external_inputs() -> None:
    for script in SCRIPTS:
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / script), "--json"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        payload = json.loads(result.stdout)
        assert payload["story_id"] in {BOOTSTRAP_STORY_ID, MANIFEST_STORY_ID, EVALUATOR_STORY_ID}
        assert payload["status"] in {
            "placeholder_contract_only",
            "manifest_builders_available",
            "action_distribution_builder_available",
            "fixture_roundtrip_passed",
            "official_reference_record_available",
        }
        assert payload["offline_only"] is True
        assert payload["config_exists"] is True
        assert result.stderr == ""
