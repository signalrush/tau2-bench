#!/usr/bin/env python3
"""Safely test whether the official direct-OpenAI transport is usable."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "reports" / "direct_openai_readiness.json"
OPENAI_BASE_URL = "https://api.openai.com/v1"
REQUIRED_MODELS = (
    "gpt-5.2",
    "gpt-4.1-2025-04-14",
    "text-embedding-3-large",
)
MAX_RESPONSE_BYTES = 1024 * 1024


class ReadinessError(RuntimeError):
    """Raised when the readiness check itself is unsafe or malformed."""


def _request_json(
    request: urllib.request.Request, *, timeout_seconds: float
) -> tuple[int, dict[str, Any]]:
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            status = int(getattr(response, "status", 200))
    except urllib.error.HTTPError as exc:
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
        status = int(exc.code)
    except (OSError, urllib.error.URLError) as exc:
        raise ReadinessError("Direct OpenAI readiness endpoint is unavailable") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ReadinessError("Direct OpenAI readiness response exceeded the size limit")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError("Direct OpenAI readiness response was not JSON") from exc
    if not isinstance(payload, dict):
        raise ReadinessError("Direct OpenAI readiness response was not an object")
    return status, payload


def _error_projection(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    error = payload.get("error")
    if not isinstance(error, dict):
        error = {}
    return {
        "http_status": status,
        "error_type": error.get("type") if isinstance(error.get("type"), str) else None,
        "error_code": error.get("code") if isinstance(error.get("code"), str) else None,
    }


def check_readiness(
    key: str, *, probe_billing: bool, timeout_seconds: float = 20.0
) -> dict[str, Any]:
    """Return a redacted receipt without retaining the credential or raw bodies."""
    if len(key) < 20 or any(character.isspace() for character in key):
        raise ReadinessError("OPENAI_API_KEY has an invalid shape")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "tau3-banking-parity-readiness/1",
    }
    model_metadata: dict[str, str] = {}
    model_errors: dict[str, dict[str, Any]] = {}
    for model in REQUIRED_MODELS:
        status, payload = _request_json(
            urllib.request.Request(
                f"{OPENAI_BASE_URL}/models/{model}", headers=headers, method="GET"
            ),
            timeout_seconds=timeout_seconds,
        )
        if status == 200 and payload.get("id") == model:
            model_metadata[model] = "accessible"
        else:
            model_metadata[model] = "blocked"
            model_errors[model] = _error_projection(status, payload)

    probe: dict[str, Any] = {
        "attempted": probe_billing,
        "model": "text-embedding-3-large",
        "input_count": 1 if probe_billing else 0,
        "embedding_values_recorded": False,
    }
    if probe_billing:
        body = json.dumps(
            {
                "model": "text-embedding-3-large",
                "input": ["tau3 parity readiness"],
            },
            separators=(",", ":"),
        ).encode("utf-8")
        status, payload = _request_json(
            urllib.request.Request(
                f"{OPENAI_BASE_URL}/embeddings",
                data=body,
                headers={**headers, "Content-Type": "application/json"},
                method="POST",
            ),
            timeout_seconds=timeout_seconds,
        )
        data = payload.get("data")
        if status == 200 and isinstance(data, list) and len(data) == 1:
            embedding = data[0].get("embedding") if isinstance(data[0], dict) else None
            if not isinstance(embedding, list) or not embedding:
                raise ReadinessError(
                    "Direct OpenAI probe returned malformed embedding data"
                )
            probe.update(
                {
                    "status": "ready",
                    "http_status": 200,
                    "embedding_dimensions": len(embedding),
                }
            )
        else:
            probe.update({"status": "blocked", **_error_projection(status, payload)})

    ready = (
        probe_billing
        and probe.get("status") == "ready"
        and all(value == "accessible" for value in model_metadata.values())
    )
    return {
        "schema_version": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "credential_locator": "env:OPENAI_API_KEY",
        "credential_present": True,
        "credential_value_recorded": False,
        "model_metadata": model_metadata,
        "model_errors": model_errors,
        "billing_probe": probe,
        "paid_evaluation_ready": ready,
        "next_gate": (
            "Build and fingerprint the complete direct-OpenAI document cache."
            if ready
            else "Resolve the redacted readiness error before any Qwen smoke or full run."
        ),
    }


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.part-",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--probe-billing", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.execute:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "credential_locator": "env:OPENAI_API_KEY",
                    "required_models": list(REQUIRED_MODELS),
                    "billing_probe": args.probe_billing,
                    "output": str(args.output),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    key = os.environ.get("OPENAI_API_KEY")
    if not isinstance(key, str):
        print("error: OPENAI_API_KEY is absent", file=os.sys.stderr)
        return 2
    try:
        receipt = check_readiness(key, probe_billing=args.probe_billing)
        write_json_atomic(args.output, receipt)
    except ReadinessError as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["paid_evaluation_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
