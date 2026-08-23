#!/usr/bin/env python3
"""Derive the Qwen 3.8 Max trial-0 parity evidence from two tau2 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def message_cost(message: dict[str, Any]) -> float:
    usage = (message.get("raw_data") or {}).get("usage") or {}
    value = usage.get("cost", 0.0)
    if isinstance(value, int | float) and math.isfinite(value) and value > 0:
        return float(value)
    outer = message.get("cost")
    if isinstance(outer, int | float) and math.isfinite(outer) and outer >= 0:
        return float(outer)
    return 0.0


def reasoning_tokens(message: dict[str, Any]) -> int:
    usage = (message.get("raw_data") or {}).get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return int(details.get("reasoning_tokens") or 0)


def simulations(data: dict[str, Any], trial: int = 0) -> list[dict[str, Any]]:
    selected = [item for item in data["simulations"] if item.get("trial") == trial]
    return sorted(selected, key=lambda item: item["task_id"])


def generated_messages(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        message
        for message in simulation["messages"]
        if message.get("role") in {"assistant", "user"} and message.get("raw_data")
    ]


def first_generated(simulation: dict[str, Any], role: str) -> dict[str, Any] | None:
    return next(
        (
            message
            for message in generated_messages(simulation)
            if message.get("role") == role
        ),
        None,
    )


def metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    generated = [message for item in items for message in generated_messages(item)]
    agent = [message for message in generated if message["role"] == "assistant"]
    user = [message for message in generated if message["role"] == "user"]
    tool_calls = [
        call
        for item in items
        for message in item["messages"]
        for call in (message.get("tool_calls") or [])
    ]
    tool_counts = Counter(call["name"] for call in tool_calls)
    terminations = Counter(item["termination_reason"] for item in items)
    judge_costs: list[float] = []
    for item in items:
        reward_info = item.get("reward_info") or {}
        judge = ((reward_info.get("info") or {}).get("nl") or {}).get("judge") or {}
        judge_usage = (judge.get("raw_response") or {}).get("usage") or {}
        judge_cost = judge_usage.get("cost")
        if isinstance(judge_cost, int | float) and math.isfinite(judge_cost):
            judge_costs.append(float(judge_cost))
    reward_sum = sum(
        float((item.get("reward_info") or {}).get("reward") or 0.0) for item in items
    )
    message_costs = {
        "assistant": math.fsum(message_cost(message) for message in agent),
        "user": math.fsum(message_cost(message) for message in user),
    }

    def token_stats(messages: list[dict[str, Any]]) -> dict[str, float | int]:
        prompt = [
            int(
                ((message.get("raw_data") or {}).get("usage") or {}).get(
                    "prompt_tokens"
                )
                or 0
            )
            for message in messages
        ]
        completion = [
            int(
                ((message.get("raw_data") or {}).get("usage") or {}).get(
                    "completion_tokens"
                )
                or 0
            )
            for message in messages
        ]
        reasoning = [reasoning_tokens(message) for message in messages]
        count = len(messages)
        return {
            "generation_count": count,
            "prompt_tokens": sum(prompt),
            "completion_tokens": sum(completion),
            "reasoning_tokens": sum(reasoning),
            "mean_prompt_tokens": sum(prompt) / count if count else 0.0,
            "mean_completion_tokens": sum(completion) / count if count else 0.0,
            "mean_reasoning_tokens": sum(reasoning) / count if count else 0.0,
        }

    count = len(items)
    return {
        "simulation_count": count,
        "reward_sum": reward_sum,
        "pass_rate_percent": 100.0 * reward_sum / count,
        "termination_counts": dict(sorted(terminations.items())),
        "infrastructure_error_count": terminations.get("infrastructure_error", 0),
        "generated_participant_message_count": len(generated),
        "generated_participant_messages_per_simulation": len(generated) / count,
        "generated_messages_by_role": {
            "assistant": len(agent),
            "user": len(user),
        },
        "tool_call_count": len(tool_calls),
        "tool_calls_per_simulation": len(tool_calls) / count,
        "distinct_tool_name_count": len(tool_counts),
        "tool_call_counts_by_name": dict(sorted(tool_counts.items())),
        "mean_duration_seconds": math.fsum(float(item["duration"]) for item in items)
        / count,
        "participant_chat_cost_usd_by_role": message_costs,
        "participant_chat_cost_usd_total": math.fsum(message_costs.values()),
        "participant_chat_cost_usd_per_simulation": math.fsum(message_costs.values())
        / count,
        "judge_call_count": len(judge_costs),
        "judge_cost_usd": math.fsum(judge_costs),
        "serialized_simulation_cost_usd": {
            "assistant": math.fsum(
                float(item.get("agent_cost") or 0.0) for item in items
            ),
            "user": math.fsum(float(item.get("user_cost") or 0.0) for item in items),
        },
        "assistant_tokens": token_stats(agent),
        "user_tokens": token_stats(user),
    }


def first_turn_evidence(
    reference: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> dict[str, Any]:
    ref_by_task = {item["task_id"]: item for item in reference}
    cand_by_task = {item["task_id"]: item for item in candidate}
    exact_user_tasks: list[str] = []
    equal_user_prompt_token_tasks: list[str] = []
    exact_agent_output_tasks: list[str] = []
    equal_agent_prompt_token_tasks: list[str] = []
    user_prompt_deltas: Counter[int] = Counter()
    for task_id in sorted(ref_by_task):
        ref_user = first_generated(ref_by_task[task_id], "user")
        cand_user = first_generated(cand_by_task[task_id], "user")
        ref_agent = first_generated(ref_by_task[task_id], "assistant")
        cand_agent = first_generated(cand_by_task[task_id], "assistant")
        if not all((ref_user, cand_user, ref_agent, cand_agent)):
            continue
        ref_user_prompt = int((ref_user.get("usage") or {}).get("prompt_tokens") or 0)
        cand_user_prompt = int((cand_user.get("usage") or {}).get("prompt_tokens") or 0)
        user_prompt_deltas[cand_user_prompt - ref_user_prompt] += 1
        if ref_user.get("content") == cand_user.get("content"):
            exact_user_tasks.append(task_id)
        if ref_user_prompt == cand_user_prompt:
            equal_user_prompt_token_tasks.append(task_id)
        ref_agent_prompt = int((ref_agent.get("usage") or {}).get("prompt_tokens") or 0)
        cand_agent_prompt = int(
            (cand_agent.get("usage") or {}).get("prompt_tokens") or 0
        )
        if ref_agent_prompt == cand_agent_prompt:
            equal_agent_prompt_token_tasks.append(task_id)
        if ref_agent.get("content") == cand_agent.get("content") and ref_agent.get(
            "tool_calls"
        ) == cand_agent.get("tool_calls"):
            exact_agent_output_tasks.append(task_id)
    exact_input_tasks = sorted(
        set(exact_user_tasks) & set(equal_agent_prompt_token_tasks)
    )
    exact_output_on_exact_input = sorted(
        set(exact_input_tasks) & set(exact_agent_output_tasks)
    )
    return {
        "exact_first_user_text_count": len(exact_user_tasks),
        "equal_first_user_prompt_token_count": len(equal_user_prompt_token_tasks),
        "first_user_prompt_token_delta_counts": {
            str(delta): count for delta, count in sorted(user_prompt_deltas.items())
        },
        "equal_first_agent_prompt_token_count": len(equal_agent_prompt_token_tasks),
        "byte_equivalent_first_agent_input_task_count": len(exact_input_tasks),
        "exact_first_agent_output_on_equivalent_input_count": len(
            exact_output_on_exact_input
        ),
        "byte_equivalent_first_agent_input_tasks": exact_input_tasks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--parity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    reference_data = json.loads(args.reference.read_text())
    candidate_data = json.loads(args.candidate.read_text())
    parity = json.loads(args.parity.read_text())
    reference = simulations(reference_data)
    candidate = simulations(candidate_data)
    ref_rewards = {
        item["task_id"]: int((item.get("reward_info") or {}).get("reward") or 0)
        for item in reference
    }
    cand_rewards = {
        item["task_id"]: int((item.get("reward_info") or {}).get("reward") or 0)
        for item in candidate
    }
    official_pass_candidate_fail = [
        task
        for task in sorted(ref_rewards)
        if ref_rewards[task] == 1 and cand_rewards[task] == 0
    ]
    official_fail_candidate_pass = [
        task
        for task in sorted(ref_rewards)
        if ref_rewards[task] == 0 and cand_rewards[task] == 1
    ]

    report = {
        "schema_version": 1,
        "reference_artifact": {
            "path": str(args.reference),
            "sha256": sha256(args.reference),
        },
        "candidate_artifact": {
            "path": str(args.candidate),
            "sha256": sha256(args.candidate),
        },
        "parity_artifact": {
            "path": str(args.parity),
            "sha256": sha256(args.parity),
        },
        "official_trial0": metrics(reference),
        "candidate_trial0": metrics(candidate),
        "reward_flips": {
            "count": len(official_pass_candidate_fail)
            + len(official_fail_candidate_pass),
            "official_pass_candidate_fail": official_pass_candidate_fail,
            "official_fail_candidate_pass": official_fail_candidate_pass,
        },
        "first_turn_evidence": first_turn_evidence(reference, candidate),
        "strict_comparator": {
            key: parity.get(key)
            for key in (
                "score_parity",
                "aggregate_score_parity",
                "reward_vector_mismatch_count",
                "component_mismatch_count",
                "structural_mismatch_count",
                "configuration_mismatch_count",
                "execution_manifest_mismatch_count",
                "raw_route_mismatch_count",
                "judge_route_mismatch_count",
                "candidate_grading_integrity_issue_count",
                "sampling_score_attribution_issue_count",
                "behavior_mismatch_count",
                "behavior_mismatch_counts",
                "model_sampling_drift_mismatch_count",
                "known_dense_drift_mismatch_count",
                "remaining_behavior_mismatch_count_after_waiver_scopes",
                "text_divergence_message_count",
                "text_divergence_message_counts",
                "tool_call_mismatch_count",
                "tool_output_mismatch_count",
                "raw_route_counters",
                "judge_route_observations",
                "strict_reproduction_parity",
            )
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
