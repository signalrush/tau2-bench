#!/usr/bin/env python3
"""Run the guarded GLM-5.2 tau3 banking evaluation."""

from __future__ import annotations

import run_nemotron_super as guarded_runner

MANIFEST_NAME = "glm52_manifest.json"
REPORT_NAME = "glm52_report.json"
BENCHMARK_ID = "tau3_banking_glm_5_2"
DEFAULT_RUN_PREFIX = "glm52"
EXPECTED_AGENT_PROVIDER = "Sail Research"
AGENT_MODEL = "openrouter/z-ai/glm-5.2"
AGENT_RESPONSE_MODEL = "z-ai/glm-5.2"
AGENT_ARGS = {
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
MODE_SPECS = {
    "smoke": {"task_ids": ("task_001",), "num_trials": 1, "credit_usd": 2.0},
    "full": {"task_ids": "all", "num_trials": 1, "credit_usd": 100.0},
}


def configure_runner() -> None:
    """Apply the GLM profile to the shared guarded-runner implementation."""
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
        setattr(guarded_runner, name, globals()[name])


def main() -> int:
    configure_runner()
    return guarded_runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
