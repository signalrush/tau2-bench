#!/usr/bin/env python3
"""Run the guarded Nemotron 3 Super tau3 banking evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shlex
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import compare_results
import run as parity_guard
from pydantic import TypeAdapter, ValidationError
from state_fingerprint import (
    StateFingerprintError,
    capture_reproduction_state,
    digest_checkpoint_artifact,
)

from tau2.data_model.message import Message

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
REFERENCE_PATH = HERE / "reference.json"
DEFAULT_CREDENTIAL_CONFIG = Path.home() / ".rllm" / "config.json"
DEFAULT_RUNS_DIR = HERE / "runs"
MANIFEST_NAME = "nemotron_super_manifest.json"
REPORT_NAME = "nemotron_super_report.json"

AGENT_MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b"
AGENT_RESPONSE_MODEL = "nvidia/nemotron-3-super-120b-a12b"
AGENT_ARGS = {
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
USER_MODEL = "openrouter/openai/gpt-5.2"
USER_ARGS = {
    "reasoning_effort": "low",
    "extra_body": {"provider": {"order": ["OpenAI"], "allow_fallbacks": False}},
}
BASE_SEED = 300
DERIVED_TRIAL_SEEDS = (626729, 373753)
MODE_SPECS = {
    "smoke": {"task_ids": ("task_001",), "num_trials": 1, "credit_usd": 1.0},
    "full": {"task_ids": "all", "num_trials": 2, "credit_usd": 40.0},
}


class NemotronRunError(RuntimeError):
    """Raised when a run cannot be proven to use the requested configuration."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_reference() -> dict[str, Any]:
    return parity_guard.load_json(REFERENCE_PATH)


def all_task_ids(reference: dict[str, Any]) -> list[str]:
    task_paths = sorted(
        (REPO_ROOT / "data/tau2/domains/banking_knowledge/tasks").glob("task_*.json")
    )
    task_ids = []
    for path in task_paths:
        task = parity_guard.load_json(path)
        task_id = task.get("id")
        if task_id != path.stem:
            raise NemotronRunError(f"Task ID/file mismatch: {path}")
        task_ids.append(task_id)
    reference_ids = set(reference.get("reward_vectors") or {})
    if (
        len(task_ids) != 97
        or len(set(task_ids)) != 97
        or set(task_ids) != reference_ids
        or "task_102" not in task_ids
    ):
        raise NemotronRunError("The checkout does not contain the exact 97-task split")
    return task_ids


def task_ids_for_mode(mode: str, reference: dict[str, Any]) -> list[str]:
    configured = MODE_SPECS[mode]["task_ids"]
    return all_task_ids(reference) if configured == "all" else list(configured)


def run_spec(mode: str, task_ids: list[str]) -> dict[str, Any]:
    num_trials = int(MODE_SPECS[mode]["num_trials"])
    return {
        "domain": "banking_knowledge",
        "agent": "llm_agent",
        "agent_model": AGENT_MODEL,
        "agent_llm_args": AGENT_ARGS,
        "user": "user_simulator",
        "user_model": USER_MODEL,
        "user_llm_args": USER_ARGS,
        "retrieval_config": "alltools",
        "task_ids": task_ids,
        "num_trials": num_trials,
        "trial_seeds": list(DERIVED_TRIAL_SEEDS[:num_trials]),
        "seed": BASE_SEED,
        "max_steps": 200,
        "max_errors": 10,
        "max_concurrency": 1 if mode == "smoke" else 10,
        "expected_simulation_count": len(task_ids) * num_trials,
        "required_openrouter_credit_usd": MODE_SPECS[mode]["credit_usd"],
    }


def build_command(spec: dict[str, Any], output_dir: Path, *, resume: bool) -> list[str]:
    command = [
        "uv",
        "run",
        "--frozen",
        "--extra",
        "knowledge",
        "tau2",
        "run",
        "--domain",
        spec["domain"],
        "--agent",
        spec["agent"],
        "--agent-llm",
        spec["agent_model"],
        "--agent-llm-args",
        json.dumps(spec["agent_llm_args"], separators=(",", ":")),
        "--user",
        spec["user"],
        "--user-llm",
        spec["user_model"],
        "--user-llm-args",
        json.dumps(spec["user_llm_args"], separators=(",", ":")),
        "--retrieval-config",
        spec["retrieval_config"],
        "--num-trials",
        str(spec["num_trials"]),
        "--max-steps",
        str(spec["max_steps"]),
        "--max-errors",
        str(spec["max_errors"]),
        "--max-concurrency",
        str(spec["max_concurrency"]),
        "--seed",
        str(spec["seed"]),
        "--log-level",
        "ERROR",
        "--save-to",
        str(output_dir),
    ]
    if resume:
        command.append("--auto-resume")
    command.extend(["--task-ids", *spec["task_ids"]])
    return command


def expected_environment(reference: dict[str, Any]) -> dict[str, str]:
    return parity_guard.expected_manifest_environment(reference)


def _nested(value: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def validate_info(
    info: dict[str, Any], spec: dict[str, Any], runtime: dict[str, Any]
) -> None:
    expected = {
        "git_commit": runtime["runtime"]["head"],
        "num_trials": spec["num_trials"],
        "max_steps": spec["max_steps"],
        "max_errors": spec["max_errors"],
        "seed": spec["seed"],
        "retrieval_config": "alltools",
        "retrieval_config_kwargs": None,
        "agent_info.implementation": "llm_agent",
        "agent_info.llm": AGENT_MODEL,
        "agent_info.llm_args": AGENT_ARGS,
        "user_info.implementation": "user_simulator",
        "user_info.llm": USER_MODEL,
        "user_info.llm_args": USER_ARGS,
        "environment_info.domain_name": "banking_knowledge",
    }
    mismatches = {}
    for field, wanted in expected.items():
        actual = _nested(info, field)
        matches = actual == wanted
        if not matches and field == "git_commit":
            # The checkpoint may trail HEAD by evaluation-only commits.
            try:
                parity_guard.evaluation_only_commit_delta(actual, wanted)
                matches = True
            except parity_guard.RunGuardError:
                matches = False
        if not matches:
            mismatches[field] = {"expected": wanted, "actual": actual}
    if mismatches:
        raise NemotronRunError(f"Checkpoint run metadata mismatch: {mismatches}")


def load_official_index(reference: dict[str, Any]) -> dict[tuple[str, int], dict]:
    trajectory = reference["artifacts"]["trajectory"]
    path = HERE / "artifacts" / trajectory["filename"]
    if path.is_symlink() or parity_guard.digest_file(path) != trajectory["sha256"]:
        raise NemotronRunError("Official grading reference artifact is not canonical")
    result = parity_guard.load_json(path)
    index, duplicates = compare_results.index_simulations(result["simulations"])
    if duplicates:
        raise NemotronRunError("Official grading reference has duplicate simulations")
    return index


def _judge_object(simulation: dict[str, Any]) -> Any:
    reward_info = simulation.get("reward_info")
    info = reward_info.get("info") if isinstance(reward_info, dict) else None
    if not isinstance(info, dict):
        return None
    judge = info.get("judge")
    if judge is None and isinstance(info.get("nl"), dict):
        judge = info["nl"].get("judge")
    return judge


def validate_participant_routes(
    simulations: list[dict[str, Any]],
    allow_missing_assistant_keys: set[tuple[str, int]] | None = None,
) -> dict[str, Any]:
    allow_missing_assistant_keys = allow_missing_assistant_keys or set()
    routes: Counter[tuple[Any, ...]] = Counter()
    response_ids: dict[str, str] = {}
    response_records = []
    costs = {"assistant": [], "user": []}
    failures = []
    for simulation in simulations:
        key = (simulation["task_id"], simulation["trial"])
        coverage = Counter()
        for index, message in enumerate(simulation.get("messages") or []):
            if not isinstance(message, dict) or message.get("role") not in {
                "assistant",
                "user",
            }:
                continue
            role = message["role"]
            raw = message.get("raw_data")
            fixed_greeting = (
                index == 0
                and role == "assistant"
                and message.get("content") == parity_guard.INITIAL_ASSISTANT_GREETING
                and raw is None
            )
            if fixed_greeting:
                continue
            response_key = f"{key[0]}:{key[1]}:{index}:{role}"
            if not isinstance(raw, dict):
                failures.append(
                    {"response": response_key, "reason": "missing_raw_data"}
                )
                continue
            failures.extend(
                compare_results.participant_raw_response_binding_issues(
                    message, response_key=response_key
                )
            )
            model = raw.get("model")
            if isinstance(model, str):
                model = model.removeprefix("openrouter/")
            route = (role, model, raw.get("provider"), raw.get("service_tier"))
            routes[route] += 1
            if role == "assistant":
                valid_route = route == (
                    "assistant",
                    AGENT_RESPONSE_MODEL,
                    "DeepInfra",
                    None,
                )
            else:
                valid_route = (
                    model
                    in {
                        "openai/gpt-5.2",
                        "openai/gpt-5.2-20251211",
                        "openai/gpt-5.2-2025-12-11",
                    }
                    and raw.get("provider") == "OpenAI"
                    and raw.get("service_tier") == "default"
                )
            if not valid_route:
                failures.append(
                    {"response": response_key, "reason": "route", "route": route}
                )
            response_id = raw.get("id")
            if not isinstance(response_id, str) or not response_id.strip():
                failures.append({"response": response_key, "reason": "response_id"})
            elif response_id in response_ids:
                failures.append(
                    {
                        "response": response_key,
                        "reason": "duplicate_response_id",
                        "first": response_ids[response_id],
                    }
                )
            else:
                response_ids[response_id] = response_key
                response_records.append([response_key, response_id])
                coverage[role] += 1
            usage = raw.get("usage")
            cost = usage.get("cost") if isinstance(usage, dict) else None
            if (
                not isinstance(cost, (int, float))
                or isinstance(cost, bool)
                or not math.isfinite(float(cost))
                or float(cost) < 0
            ):
                failures.append({"response": response_key, "reason": "usage_cost"})
            else:
                costs[role].append(float(cost))
        if coverage["user"] < 1 or (
            coverage["assistant"] < 1 and key not in allow_missing_assistant_keys
        ):
            failures.append({"simulation": list(key), "reason": "route_coverage"})
    if failures:
        raise NemotronRunError(f"Participant route validation failed: {failures[:20]}")
    route_rows = [
        {
            "role": role,
            "model": model,
            "provider": provider,
            "service_tier": tier,
            "count": count,
        }
        for (role, model, provider, tier), count in sorted(
            routes.items(), key=lambda item: repr(item[0])
        )
    ]
    return {
        "routes": route_rows,
        "response_id_count": len(response_records),
        "response_ids_sha256": canonical_digest(sorted(response_records)),
        "cost_usd_by_role": {
            role: math.fsum(values) for role, values in sorted(costs.items())
        },
        "participant_cost_usd": math.fsum(
            value for values in costs.values() for value in values
        ),
        "response_ids": set(response_ids),
    }


def validate_checkpoint(
    results_path: Path,
    spec: dict[str, Any],
    runtime: dict[str, Any],
    reference: dict[str, Any],
    *,
    complete: bool,
) -> dict[str, Any]:
    checkpoint = parity_guard._load_checkpoint(results_path)
    validate_info(checkpoint["info"], spec, runtime)
    task_ids = [
        task.get("id") for task in checkpoint["tasks"] if isinstance(task, dict)
    ]
    if len(task_ids) != len(set(task_ids)) or set(task_ids) != set(spec["task_ids"]):
        raise NemotronRunError("Checkpoint task set is not exact")
    expected_keys = {
        (task_id, trial)
        for task_id in spec["task_ids"]
        for trial in range(spec["num_trials"])
    }
    actual_keys = set()
    simulation_ids = set()
    infrastructure = []
    completed = []
    official = load_official_index(reference)
    grading_failures = []
    for simulation in checkpoint["simulations"]:
        if not isinstance(simulation, dict):
            raise NemotronRunError("Checkpoint contains a malformed simulation")
        key = (simulation.get("task_id"), simulation.get("trial"))
        simulation_id = simulation.get("id")
        if key not in expected_keys or key in actual_keys:
            raise NemotronRunError(f"Checkpoint has an invalid/duplicate key: {key}")
        if not isinstance(simulation_id, str) or simulation_id in simulation_ids:
            raise NemotronRunError("Checkpoint has an invalid/duplicate simulation ID")
        actual_keys.add(key)
        simulation_ids.add(simulation_id)
        try:
            parsed_messages = TypeAdapter(list[Message]).validate_python(
                simulation.get("messages") or []
            )
        except ValidationError as exc:
            raise NemotronRunError(
                f"Checkpoint message schema failed for {key}: {exc.errors()[:5]}"
            ) from None
        if simulation.get("seed") != spec["trial_seeds"][key[1]]:
            raise NemotronRunError(f"Checkpoint seed mismatch for {key}")
        termination = simulation.get("termination_reason")
        if termination == "infrastructure_error":
            infrastructure.append(key)
            if simulation.get("reward_info") is not None:
                raise NemotronRunError(f"Infrastructure failure has a reward: {key}")
            continue
        role_costs = {
            role: math.fsum(
                float(message.get("cost"))
                for message in simulation.get("messages") or []
                if isinstance(message, dict)
                and message.get("role") == role
                and isinstance(message.get("cost"), (int, float))
                and not isinstance(message.get("cost"), bool)
            )
            for role in ("assistant", "user")
        }
        for field, role in (("agent_cost", "assistant"), ("user_cost", "user")):
            serialized_cost = simulation.get(field)
            if (
                not isinstance(serialized_cost, (int, float))
                or isinstance(serialized_cost, bool)
                or not math.isfinite(float(serialized_cost))
                or float(serialized_cost) < 0
                or not math.isclose(
                    float(serialized_cost),
                    role_costs[role],
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                raise NemotronRunError(f"Simulation {field} is invalid for {key}")
        duration = simulation.get("duration")
        if (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or not math.isfinite(float(duration))
            or float(duration) < 0
        ):
            raise NemotronRunError(f"Simulation duration is invalid for {key}")
        protocol_issues = compare_results.message_protocol_issues(
            parsed_messages, require_user_terminal=termination == "user_stop"
        )
        if protocol_issues:
            raise NemotronRunError(
                f"Checkpoint message protocol failed for {key}: {protocol_issues[:10]}"
            )
        reward_info = simulation.get("reward_info")
        reward = reward_info.get("reward") if isinstance(reward_info, dict) else None
        if reward not in {0, 0.0, 1, 1.0} or isinstance(reward, bool):
            raise NemotronRunError(f"Simulation has a non-binary reward: {key}")
        if termination not in {
            "user_stop",
            "agent_stop",
            "max_steps",
            "too_many_errors",
            "agent_error",
            "context_window_exceeded",
        }:
            raise NemotronRunError(
                f"Non-agent termination cannot be accepted as model performance: {key}"
            )
        if termination not in {"user_stop", "agent_stop"}:
            if (
                float(reward) != 0.0
                or reward_info.get("reward_basis") is not None
                or not isinstance(reward_info.get("info"), dict)
            ):
                raise NemotronRunError(
                    f"Premature termination is not serialized as a zero: {key}"
                )
            completed.append(simulation)
            continue
        completed.append(simulation)
        grading_failures.extend(
            {"key": list(key), **issue}
            for issue in compare_results.grading_integrity_issues(
                simulation, official[key]
            )
        )
    if grading_failures:
        raise NemotronRunError(f"Grading integrity failed: {grading_failures[:20]}")
    if complete and actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        raise NemotronRunError(
            f"Incomplete Cartesian task/trial coverage: {missing[:20]}"
        )
    if complete and infrastructure:
        raise NemotronRunError(f"Infrastructure failures remain: {infrastructure}")
    participant = (
        validate_participant_routes(
            completed,
            {
                (s["task_id"], s["trial"])
                for s in completed
                if s["termination_reason"] in {"agent_error", "context_window_exceeded"}
            },
        )
        if completed
        else {
            "routes": [],
            "response_id_count": 0,
            "response_ids_sha256": canonical_digest([]),
            "cost_usd_by_role": {"assistant": 0.0, "user": 0.0},
            "participant_cost_usd": 0.0,
            "response_ids": set(),
        }
    )
    expected_judge_keys = {
        (simulation["task_id"], simulation["trial"])
        for simulation in completed
        if simulation["task_id"] == "task_102"
        and isinstance(simulation["reward_info"].get("reward_basis"), list)
        and "NL_ASSERTION" in simulation["reward_info"]["reward_basis"]
    }
    judge = compare_results.validate_judge_routes(
        {"simulations": completed}, sorted(expected_judge_keys), reference
    )
    expected_judge_count = len(expected_judge_keys)
    actual_judge_keys = {
        (s["task_id"], s["trial"]) for s in completed if _judge_object(s) is not None
    }
    if (
        actual_judge_keys != expected_judge_keys
        or (expected_judge_count and judge.get("judge_route_parity") is not True)
        or (not expected_judge_count and judge.get("judge_route_checked") is not False)
    ):
        raise NemotronRunError(
            f"task_102 judge route validation failed: {judge.get('judge_route_mismatches')}"
        )
    judge_costs = []
    judge_ids = []
    for simulation in completed:
        judge_object = _judge_object(simulation)
        if not isinstance(judge_object, dict):
            continue
        response_id = judge_object.get("response_id")
        raw = judge_object.get("raw_response")
        usage = raw.get("usage") if isinstance(raw, dict) else None
        cost = usage.get("cost") if isinstance(usage, dict) else None
        if (
            not isinstance(cost, (int, float))
            or isinstance(cost, bool)
            or not math.isfinite(float(cost))
            or float(cost) < 0
        ):
            raise NemotronRunError("Judge response lacks a numeric cost")
        if response_id in participant["response_ids"]:
            raise NemotronRunError("Judge and participant response IDs collide")
        judge_ids.append(response_id)
        judge_costs.append(float(cost))
    rewards = [float(s["reward_info"]["reward"]) for s in completed]
    by_trial = {
        str(trial): math.fsum(
            float(s["reward_info"]["reward"]) for s in completed if s["trial"] == trial
        )
        for trial in range(spec["num_trials"])
    }
    by_task = {
        task_id: [
            int(float(simulation["reward_info"]["reward"]))
            for trial in range(spec["num_trials"])
            for simulation in completed
            if simulation["task_id"] == task_id and simulation["trial"] == trial
        ]
        for task_id in spec["task_ids"]
    }
    termination_counts = dict(
        sorted(Counter(s["termination_reason"] for s in completed).items())
    )
    participant.pop("response_ids")
    return {
        "validation_passed": complete,
        "expected_simulation_count": len(expected_keys),
        "actual_simulation_count": len(actual_keys),
        "completed_simulation_count": len(completed),
        "infrastructure_error_count": len(infrastructure),
        "coverage_sha256": canonical_digest(sorted([a, b] for a, b in actual_keys)),
        "reward_sum": math.fsum(rewards),
        "pass_rate_percent": 100.0 * math.fsum(rewards) / len(expected_keys)
        if complete
        else None,
        "reward_sum_by_trial": by_trial,
        "reward_vectors_by_task": by_task,
        "termination_counts": termination_counts,
        "participant_routes": participant["routes"],
        "participant_response_id_count": participant["response_id_count"],
        "participant_response_ids_sha256": participant["response_ids_sha256"],
        "participant_cost_usd_by_role": participant["cost_usd_by_role"],
        "participant_cost_usd": participant["participant_cost_usd"],
        "judge_route_observations": judge["judge_route_observations"],
        "judge_response_id_count": len(judge_ids),
        "judge_response_ids_sha256": canonical_digest(sorted(judge_ids)),
        "judge_cost_usd": math.fsum(judge_costs),
        "serialized_chat_cost_usd": participant["participant_cost_usd"]
        + math.fsum(judge_costs),
        "cost_scope": "serialized agent, user, and NL-judge costs; excludes embeddings and Modal",
    }


def static_manifest(
    mode: str,
    spec: dict[str, Any],
    output_dir: Path,
    environment: dict[str, str],
    runtime: dict[str, Any],
    reference: dict[str, Any],
    smoke_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    initial_command = build_command(spec, output_dir, resume=False)
    order = parity_guard.verify_modal_order_manifest(reference)
    shell_receipt = parity_guard.verify_full_shell_oracle_receipt(
        reference, allow_known_drift=True
    )
    return {
        "schema_version": 1,
        "benchmark": "tau3_banking_nemotron_3_super",
        "mode": mode,
        "output_dir": str(output_dir),
        "run_spec": spec,
        "run_spec_sha256": canonical_digest(spec),
        "reference_config_sha256": parity_guard.digest_file(REFERENCE_PATH),
        "task_ids_sha256": canonical_digest(spec["task_ids"]),
        "initial_command": initial_command,
        "initial_command_sha256": canonical_digest(initial_command),
        "environment": environment,
        "environment_sha256": canonical_digest(environment),
        "execution_state": runtime,
        "modal_order_manifest_sha256": parity_guard.digest_file(
            REPO_ROOT / parity_guard.MODAL_ORDER_MANIFEST_RELATIVE
        ),
        "modal_order_sha256": order["order_sha256"],
        "modal_image_object_id": reference["reproduction_transport"][
            "modal_image_object_id"
        ],
        "modal_shell_oracle_sha256": reference["reproduction_transport"][
            "full_shell_oracle_receipt_integrity"
        ]["file_sha256"],
        "modal_known_shell_drift_count": shell_receipt["mismatch_command_count"],
        "verified_smoke_receipt": smoke_receipt,
    }


def verify_smoke_manifest(
    manifest_path: Path,
    runtime: dict[str, Any],
    reference: dict[str, Any],
) -> dict[str, Any]:
    """Bind a full launch to a completed smoke from this exact runtime."""
    manifest_path = manifest_path.expanduser().resolve()
    if manifest_path.name != MANIFEST_NAME or manifest_path.is_symlink():
        raise NemotronRunError("Full mode requires a canonical smoke manifest file")
    manifest = parity_guard.load_json(manifest_path)
    output_dir = Path(manifest.get("output_dir", "")).expanduser().resolve()
    if manifest_path != output_dir / MANIFEST_NAME:
        raise NemotronRunError("Smoke manifest/output path binding is invalid")
    smoke_spec = run_spec("smoke", ["task_001"])
    expected_command = build_command(smoke_spec, output_dir, resume=False)
    smoke_environment = expected_environment(reference)
    if (
        manifest.get("benchmark") != "tau3_banking_nemotron_3_super"
        or manifest.get("mode") != "smoke"
        or manifest.get("status") != "completed"
        or manifest.get("exit_code") != 0
        or manifest.get("runner_exit_code") != 0
        or manifest.get("run_spec") != smoke_spec
        or manifest.get("run_spec_sha256") != canonical_digest(smoke_spec)
        or manifest.get("initial_command") != expected_command
        or manifest.get("environment") != smoke_environment
        or not parity_guard._state_matches_current_or_evaluation_delta(
            manifest.get("execution_state"), runtime
        )
    ):
        raise NemotronRunError("Smoke manifest does not match the current full runtime")
    launches = manifest.get("launches")
    if not isinstance(launches, list) or not launches:
        raise NemotronRunError("Smoke manifest has no completed launch receipt")
    previous_after = None
    for index, launch in enumerate(launches):
        if not isinstance(launch, dict):
            raise NemotronRunError("Smoke launch receipt is malformed")
        expected_launch_command = build_command(
            smoke_spec, output_dir, resume=index > 0
        )
        if (
            launch.get("command") != expected_launch_command
            or launch.get("command_sha256") != canonical_digest(expected_launch_command)
            or launch.get("checkpoint_sha256_before") != previous_after
        ):
            raise NemotronRunError("Smoke launch command/hash chain is invalid")
        is_last = index == len(launches) - 1
        status = launch.get("status")
        if status not in {"completed", "failed", "interrupted_recovered"}:
            raise NemotronRunError("Smoke launch status receipt is invalid")
        if is_last and (status != "completed" or launch.get("runner_exit_code") != 0):
            raise NemotronRunError("Smoke final launch did not complete successfully")
        after = launch.get("checkpoint_sha256_after")
        if not isinstance(after, str) or len(after) != 64:
            raise NemotronRunError("Smoke launch lacks a checkpoint digest")
        previous_after = after
    results_path = output_dir / "results.json"
    report_path = output_dir / REPORT_NAME
    if not results_path.is_file() or not report_path.is_file():
        raise NemotronRunError("Smoke result/report artifact is missing")
    results_sha256 = digest_checkpoint_artifact(results_path)
    report_file_sha256 = parity_guard.digest_file(report_path)
    report = parity_guard.load_json(report_path)
    if (
        manifest.get("checkpoint_sha256") != results_sha256
        or previous_after != results_sha256
        or manifest.get("report_file_sha256") != report_file_sha256
        or manifest.get("report") != report
        or report.get("validation_passed") is not True
        or report.get("mode") != "smoke"
        or report.get("expected_simulation_count") != 1
        or report.get("actual_simulation_count") != 1
        or report.get("infrastructure_error_count") != 0
        or report.get("runtime_digest") != _nested(manifest, "execution_state.digest")
        or report.get("results_sha256") != results_sha256
        or report.get("run_spec_sha256") != canonical_digest(smoke_spec)
    ):
        raise NemotronRunError("Smoke result/report receipt is invalid")
    routes = report.get("participant_routes")
    observed = (
        {
            (row.get("role"), row.get("provider"))
            for row in routes
            if isinstance(row, dict) and row.get("count", 0) > 0
        }
        if isinstance(routes, list)
        else set()
    )
    if observed != {("assistant", "DeepInfra"), ("user", "OpenAI")}:
        raise NemotronRunError("Smoke did not prove the exact participant routes")
    return {
        "manifest_path": str(manifest_path),
        "manifest_sha256": parity_guard.digest_file(manifest_path),
        "results_sha256": results_sha256,
        "report_sha256": report_file_sha256,
        "report_digest": report.get("report_digest"),
        # Bound to the smoke's own recorded runtime state (equal to the
        # launch-time runtime at creation), so evaluation-only commits after
        # the smoke do not orphan an otherwise valid receipt.
        "runtime_digest": _nested(manifest, "execution_state.digest"),
    }


def validate_resume_manifest(
    manifest: dict[str, Any], expected_static: dict[str, Any], results_path: Path
) -> bool:
    """Validate a finalized manifest or identify one crash-interrupted launch."""
    strict_keys = [key for key in expected_static if key != "execution_state"]
    actual_static = {key: manifest.get(key) for key in strict_keys}
    if actual_static != {key: expected_static[key] for key in strict_keys}:
        raise NemotronRunError(
            "Resume manifest does not match the current clean runtime"
        )
    # The recorded execution state may trail the current runtime only by
    # evaluation-only commits with an unchanged embedding cache.
    if not parity_guard._state_matches_current_or_evaluation_delta(
        manifest.get("execution_state"), expected_static["execution_state"]
    ):
        raise NemotronRunError(
            "Resume manifest runtime state differs beyond an evaluation-only "
            "commit delta"
        )
    launches = manifest.get("launches")
    if not isinstance(launches, list) or not launches:
        raise NemotronRunError("Resume manifest has no prior guarded launch")
    previous_after = None
    interrupted = False
    for index, launch in enumerate(launches):
        if not isinstance(launch, dict):
            raise NemotronRunError("Resume launch receipt is malformed")
        command = build_command(
            expected_static["run_spec"],
            Path(expected_static["output_dir"]),
            resume=index > 0,
        )
        if (
            launch.get("resume") is not (index > 0)
            or launch.get("command") != command
            or launch.get("command_sha256") != canonical_digest(command)
            or launch.get("checkpoint_sha256_before") != previous_after
        ):
            raise NemotronRunError("Resume launch hash chain is invalid")
        is_last = index == len(launches) - 1
        if launch.get("status") == "running" and is_last:
            interrupted = True
            break
        if launch.get("status") not in {"completed", "failed", "interrupted_recovered"}:
            raise NemotronRunError("Resume launch status is invalid")
        after = launch.get("checkpoint_sha256_after")
        if not isinstance(after, str) or len(after) != 64:
            raise NemotronRunError("Resume launch lacks a finalized checkpoint digest")
        previous_after = after
    if manifest.get("status") == "completed":
        raise NemotronRunError("Completed evaluation does not need resume")
    if interrupted != (manifest.get("status") == "running"):
        raise NemotronRunError("Resume manifest/launch status is inconsistent")
    current_digest = digest_checkpoint_artifact(results_path)
    if not interrupted and (
        manifest.get("checkpoint_sha256") != current_digest
        or previous_after != current_digest
    ):
        raise NemotronRunError("Resume checkpoint changed after manifest finalization")
    return interrupted


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=tuple(MODE_SPECS))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--credential-config", type=Path, default=DEFAULT_CREDENTIAL_CONFIG
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-paid-api-calls", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--smoke-manifest",
        type=Path,
        help="Completed same-commit smoke receipt required by full mode",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        reference = load_reference()
        parity_guard.verify_checkout(reference)
        parity_guard.verify_runtime_patches(reference)
        task_ids = task_ids_for_mode(args.mode, reference)
        spec = run_spec(args.mode, task_ids)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = (
            args.output_dir.expanduser().resolve()
            if args.output_dir
            else (
                DEFAULT_RUNS_DIR / f"nemotron_super_{args.mode}_{timestamp}"
            ).resolve()
        )
        results_path = output_dir / "results.json"
        manifest_path = output_dir / MANIFEST_NAME
        report_path = output_dir / REPORT_NAME
        command = build_command(spec, output_dir, resume=args.resume)
        environment_receipt = expected_environment(reference)
        plan = {
            "mode": args.mode,
            "output_dir": str(output_dir),
            "run_spec": spec,
            "command": command,
            "environment": environment_receipt,
            "resume": args.resume,
            "execute": args.execute,
            "smoke_manifest": str(args.smoke_manifest) if args.smoke_manifest else None,
        }
        print(json.dumps(plan, indent=2, sort_keys=True))
        print(f"\nargv: {shlex.join(command)}")
        if not args.execute:
            print(
                "\nDry run only. No model, embedding, Modal, or credit API calls were made."
            )
            return 0
        if not args.confirm_paid_api_calls:
            raise NemotronRunError("--execute requires --confirm-paid-api-calls")
        if args.mode == "full" and args.smoke_manifest is None:
            raise NemotronRunError("Full execution requires --smoke-manifest")
        if args.mode == "smoke" and args.smoke_manifest is not None:
            raise NemotronRunError("--smoke-manifest is valid only for full mode")
        if (
            args.credential_config.expanduser().resolve()
            != DEFAULT_CREDENTIAL_CONFIG.resolve()
        ):
            raise NemotronRunError("Paid execution requires ~/.rllm/config.json")
        parity_guard.verify_modal_credentials(os.environ)
        if args.resume:
            if not results_path.is_file() or not manifest_path.is_file():
                raise NemotronRunError(
                    "Resume requires results.json and its guarded manifest"
                )
        elif output_dir.exists():
            raise NemotronRunError(
                "New paid execution requires a fresh output directory"
            )
        runtime = capture_reproduction_state(
            REPO_ROOT, require_clean=True, require_cache=True
        )
        smoke_receipt = (
            verify_smoke_manifest(args.smoke_manifest, runtime, reference)
            if args.mode == "full" and args.smoke_manifest is not None
            else None
        )
        static = static_manifest(
            args.mode,
            spec,
            output_dir,
            environment_receipt,
            runtime,
            reference,
            smoke_receipt,
        )
        key = parity_guard.load_openrouter_key(args.credential_config, os.environ)
        credit = parity_guard.fetch_openrouter_credit_state(
            key, float(spec["required_openrouter_credit_usd"])
        )
        paid_environment = parity_guard.build_paid_environment(key, environment_receipt)
        with parity_guard.hold_output_run_lock(output_dir) as lock_handle:
            locked_runtime = capture_reproduction_state(
                REPO_ROOT, require_clean=True, require_cache=True
            )
            if locked_runtime["digest"] != runtime["digest"]:
                raise NemotronRunError("Runtime changed while waiting for output lock")
            if args.resume:
                manifest = parity_guard.load_json(manifest_path)
                interrupted = validate_resume_manifest(manifest, static, results_path)
                validate_checkpoint(
                    results_path, spec, runtime, reference, complete=False
                )
                if interrupted:
                    recovered_digest = digest_checkpoint_artifact(results_path)
                    recovered_launch = manifest["launches"][-1]
                    recovered_launch.update(
                        {
                            "completed_at": utc_now(),
                            "status": "interrupted_recovered",
                            "runner_exit_code": None,
                            "checkpoint_sha256_after": recovered_digest,
                        }
                    )
                    manifest["status"] = "interrupted_recovered"
                    manifest["checkpoint_sha256"] = recovered_digest
                    parity_guard.write_json_atomic(manifest_path, manifest)
            else:
                unexpected_entries = [
                    path.name
                    for path in output_dir.iterdir()
                    if path.name != ".tau3_banking_run.lock"
                ]
                if unexpected_entries:
                    raise NemotronRunError(
                        "Fresh output directory changed before lock acquisition: "
                        f"{sorted(unexpected_entries)}"
                    )
                manifest = {
                    **static,
                    "created_at": utc_now(),
                    "status": "created",
                    "launches": [],
                }
            launch = {
                "started_at": utc_now(),
                "resume": args.resume,
                "command": command,
                "command_sha256": canonical_digest(command),
                "credit_preflight": credit,
                "checkpoint_sha256_before": digest_checkpoint_artifact(results_path)
                if results_path.exists()
                else None,
                "status": "running",
            }
            manifest["launches"].append(launch)
            manifest["status"] = "running"
            manifest["checkpoint_sha256"] = launch["checkpoint_sha256_before"]
            parity_guard.write_json_atomic(manifest_path, manifest)
            try:
                process = subprocess.run(
                    command,
                    cwd=REPO_ROOT,
                    env=paid_environment,
                    check=False,
                    pass_fds=(lock_handle.fileno(),),
                )
                exit_code = process.returncode
            except KeyboardInterrupt:
                exit_code = 130
                launch["runner_exception_type"] = "KeyboardInterrupt"
            except Exception as exc:
                exit_code = 2
                launch["runner_exception_type"] = type(exc).__name__
            launch["completed_at"] = utc_now()
            launch["runner_exit_code"] = exit_code
            launch["status"] = "completed" if exit_code == 0 else "failed"
            manifest["checkpoint_sha256"] = (
                digest_checkpoint_artifact(results_path)
                if results_path.exists()
                else None
            )
            launch["checkpoint_sha256_after"] = manifest["checkpoint_sha256"]
            manifest["completed_at"] = utc_now()
            manifest["runner_exit_code"] = exit_code
            if exit_code == 0:
                try:
                    report = validate_checkpoint(
                        results_path, spec, runtime, reference, complete=True
                    )
                    report.update(
                        {
                            "schema_version": 1,
                            "mode": args.mode,
                            "results_sha256": manifest["checkpoint_sha256"],
                            "runtime_digest": runtime["digest"],
                            "run_spec_sha256": static["run_spec_sha256"],
                            "task_ids_sha256": static["task_ids_sha256"],
                            "generated_at": utc_now(),
                        }
                    )
                    report["report_digest"] = canonical_digest(report)
                    parity_guard.write_json_atomic(report_path, report)
                    manifest["report"] = report
                    manifest["report_file_sha256"] = parity_guard.digest_file(
                        report_path
                    )
                    manifest["status"] = "completed"
                except Exception as exc:
                    manifest["status"] = "post_run_validation_failed"
                    manifest["validation_error"] = {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
                    exit_code = 2
            else:
                manifest["status"] = "failed"
            manifest["exit_code"] = exit_code
            try:
                post_run_state = capture_reproduction_state(
                    REPO_ROOT, require_clean=True, require_cache=True
                )
                if post_run_state["digest"] != runtime["digest"]:
                    raise NemotronRunError("Runtime changed during the paid launch")
                if results_path.exists() and digest_checkpoint_artifact(
                    results_path
                ) != manifest.get("checkpoint_sha256"):
                    raise NemotronRunError("Checkpoint changed during final validation")
                manifest["post_run_execution_state"] = post_run_state
            except Exception as exc:
                manifest["status"] = "finalization_failed"
                manifest["finalization_error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
                exit_code = 2
                manifest["exit_code"] = exit_code
            parity_guard.write_json_atomic(manifest_path, manifest)
        if exit_code == 0:
            print(json.dumps(manifest["report"], indent=2, sort_keys=True))
        return exit_code
    except (
        NemotronRunError,
        parity_guard.RunGuardError,
        StateFingerprintError,
        KeyError,
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
