"""Offline tests for the guarded GLM-5.2 banking profile."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_DIR = REPO_ROOT / "reproduction" / "tau3_banking"
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

import run_glm52  # noqa: E402

runner = run_glm52.guarded_runner


@pytest.fixture
def glm_runner(monkeypatch):
    for name in (
        "MANIFEST_NAME",
        "REPORT_NAME",
        "BENCHMARK_ID",
        "DEFAULT_RUN_PREFIX",
        "EXPECTED_AGENT_PROVIDER",
        "AGENT_MODEL",
        "AGENT_RESPONSE_MODEL",
        "AGENT_ARGS",
        "MODE_SPECS",
    ):
        monkeypatch.setattr(runner, name, getattr(run_glm52, name))
    return runner


def test_glm52_full_spec_is_exact_97_by_1_contract(glm_runner):
    runner = glm_runner
    reference = runner.load_reference()
    task_ids = runner.task_ids_for_mode("full", reference)
    spec = runner.run_spec("full", task_ids)

    assert len(task_ids) == 97
    assert spec["num_trials"] == 1
    assert spec["expected_simulation_count"] == 97
    assert spec["trial_seeds"] == [626729]
    assert spec["max_concurrency"] == 10
    assert spec["required_openrouter_credit_usd"] == 100.0
    assert spec["agent_model"] == "openrouter/z-ai/glm-5.2"
    assert spec["agent_llm_args"] == {
        "temperature": 1.0,
        "top_p": 1.0,
        "max_tokens": 16384,
        "extra_body": {
            "reasoning": {"effort": "xhigh"},
            "provider": {
                "order": ["Sail Research"],
                "allow_fallbacks": False,
                "require_parameters": True,
            },
        },
    }


def test_glm52_smoke_command_is_fresh_one_by_one(glm_runner, tmp_path):
    runner = glm_runner
    spec = runner.run_spec("smoke", ["task_001"])
    command = runner.build_command(spec, tmp_path, resume=False)
    rendered = " ".join(command)

    assert command[command.index("--num-trials") + 1] == "1"
    assert command[command.index("--max-concurrency") + 1] == "1"
    assert command[command.index("--task-ids") + 1 :] == ["task_001"]
    assert "OPENROUTER_API_KEY" not in rendered
    assert json.loads(command[command.index("--agent-llm-args") + 1]) == (
        runner.AGENT_ARGS
    )


def test_glm52_profile_has_distinct_receipts_and_route():
    assert run_glm52.BENCHMARK_ID == "tau3_banking_glm_5_2"
    assert run_glm52.MANIFEST_NAME == "glm52_manifest.json"
    assert run_glm52.REPORT_NAME == "glm52_report.json"
    assert run_glm52.DEFAULT_RUN_PREFIX == "glm52"
    assert run_glm52.EXPECTED_AGENT_PROVIDER == "Sail Research"
