"""Offline tests for the guarded Nemotron 3 Super banking runner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_DIR = REPO_ROOT / "reproduction" / "tau3_banking"
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

import run_nemotron_super as nemotron_run  # noqa: E402


def _raw_message(role: str, response_id: str, *, provider: str) -> dict:
    model = (
        "nvidia/nemotron-3-super-120b-a12b" if role == "assistant" else "openai/gpt-5.2"
    )
    service_tier = None if role == "assistant" else "default"
    usage = {"prompt_tokens": 10, "completion_tokens": 2}
    return {
        "role": role,
        "content": "generated response",
        "cost": 0.01,
        "usage": usage,
        "raw_data": {
            "id": response_id,
            "model": model,
            "provider": provider,
            "service_tier": service_tier,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "generated response",
                        "tool_calls": None,
                    },
                }
            ],
            "usage": {**usage, "cost": 0.01},
        },
    }


def test_full_spec_is_exact_97_by_2_contract():
    reference = nemotron_run.load_reference()
    task_ids = nemotron_run.task_ids_for_mode("full", reference)
    spec = nemotron_run.run_spec("full", task_ids)

    assert len(task_ids) == 97
    assert spec["num_trials"] == 2
    assert spec["expected_simulation_count"] == 194
    assert spec["trial_seeds"] == [626729, 373753]
    assert spec["required_openrouter_credit_usd"] == 40.0
    assert spec["max_concurrency"] == 10
    assert spec["agent_model"] == ("openrouter/nvidia/nemotron-3-super-120b-a12b")
    assert spec["agent_llm_args"] == {
        "temperature": 1.0,
        "top_p": 0.95,
        "max_tokens": 16000,
        "extra_body": {
            "reasoning": {"effort": "medium"},
            "provider": {
                "order": ["DeepInfra"],
                "allow_fallbacks": False,
                "require_parameters": True,
            },
        },
    }


def test_smoke_command_is_one_task_one_trial_and_has_no_secret(tmp_path):
    spec = nemotron_run.run_spec("smoke", ["task_001"])
    command = nemotron_run.build_command(spec, tmp_path, resume=False)
    rendered = " ".join(command)

    assert spec["required_openrouter_credit_usd"] == 1.0
    assert command[command.index("--num-trials") + 1] == "1"
    assert command[command.index("--max-concurrency") + 1] == "1"
    assert command[command.index("--task-ids") + 1 :] == ["task_001"]
    assert "OPENROUTER_API_KEY" not in rendered
    agent_args = json.loads(command[command.index("--agent-llm-args") + 1])
    user_args = json.loads(command[command.index("--user-llm-args") + 1])
    assert agent_args == nemotron_run.AGENT_ARGS
    assert user_args == nemotron_run.USER_ARGS


def test_resume_is_the_only_path_that_adds_auto_resume(tmp_path):
    spec = nemotron_run.run_spec("smoke", ["task_001"])

    assert "--auto-resume" not in nemotron_run.build_command(
        spec, tmp_path, resume=False
    )
    assert "--auto-resume" in nemotron_run.build_command(spec, tmp_path, resume=True)


def test_participant_routes_require_deepinfra_and_openai():
    simulation = {
        "task_id": "task_001",
        "trial": 0,
        "messages": [
            _raw_message("assistant", "agent-1", provider="DeepInfra"),
            _raw_message("user", "user-1", provider="OpenAI"),
        ],
    }

    report = nemotron_run.validate_participant_routes([simulation], {("task_001", 0)})

    assert report["response_id_count"] == 2
    assert report["participant_cost_usd"] == pytest.approx(0.02)
    assert {row["provider"] for row in report["routes"]} == {
        "DeepInfra",
        "OpenAI",
    }


def test_participant_routes_accept_token_limit_finish_reason():
    assistant = _raw_message("assistant", "agent-1", provider="DeepInfra")
    assistant["raw_data"]["choices"][0]["finish_reason"] = "length"
    simulation = {
        "task_id": "task_001",
        "trial": 0,
        "messages": [
            assistant,
            _raw_message("user", "user-1", provider="OpenAI"),
        ],
    }

    report = nemotron_run.validate_participant_routes([simulation])

    assert report["response_id_count"] == 2


def test_participant_routes_reject_unbound_finish_reason():
    assistant = _raw_message("assistant", "agent-1", provider="DeepInfra")
    assistant["raw_data"]["choices"][0]["finish_reason"] = "content_filter"
    simulation = {
        "task_id": "task_001",
        "trial": 0,
        "messages": [
            assistant,
            _raw_message("user", "user-1", provider="OpenAI"),
        ],
    }

    with pytest.raises(nemotron_run.NemotronRunError, match="route validation"):
        nemotron_run.validate_participant_routes([simulation])


def test_participant_routes_reject_agent_fallback_provider():
    simulation = {
        "task_id": "task_001",
        "trial": 0,
        "messages": [
            _raw_message("assistant", "agent-1", provider="DigitalOcean"),
            _raw_message("user", "user-1", provider="OpenAI"),
        ],
    }

    with pytest.raises(nemotron_run.NemotronRunError, match="route validation"):
        nemotron_run.validate_participant_routes([simulation], {("task_001", 0)})
