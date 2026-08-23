"""Offline tests for the redacted direct-OpenAI readiness gate."""

from __future__ import annotations

import importlib.util
import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "reproduction/tau3_banking/check_direct_openai.py"
SPEC = importlib.util.spec_from_file_location("direct_openai_readiness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
readiness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(readiness)


class Response(BytesIO):
    def __init__(self, payload: dict, status: int = 200):
        super().__init__(json.dumps(payload).encode("utf-8"))
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_ready_receipt_never_contains_key_or_embedding(monkeypatch):
    def urlopen(request, timeout):
        assert timeout == 20.0
        if request.full_url.endswith("/embeddings"):
            return Response({"data": [{"embedding": [0.1, 0.2, 0.3]}]})
        model = request.full_url.rsplit("/", 1)[-1]
        return Response({"id": model})

    monkeypatch.setattr(readiness.urllib.request, "urlopen", urlopen)
    receipt = readiness.check_readiness("k" * 24, probe_billing=True)
    serialized = json.dumps(receipt)

    assert receipt["paid_evaluation_ready"] is True
    assert receipt["billing_probe"]["embedding_dimensions"] == 3
    assert "kkkk" not in serialized
    assert "0.1" not in serialized


def test_billing_inactive_is_redacted_and_blocks(monkeypatch):
    def urlopen(request, timeout):
        if request.full_url.endswith("/embeddings"):
            body = json.dumps(
                {
                    "error": {
                        "message": "private account detail",
                        "type": "billing_not_active",
                        "code": "billing_not_active",
                    }
                }
            ).encode("utf-8")
            raise HTTPError(request.full_url, 429, "blocked", {}, BytesIO(body))
        model = request.full_url.rsplit("/", 1)[-1]
        return Response({"id": model})

    monkeypatch.setattr(readiness.urllib.request, "urlopen", urlopen)
    receipt = readiness.check_readiness("k" * 24, probe_billing=True)
    serialized = json.dumps(receipt)

    assert receipt["paid_evaluation_ready"] is False
    assert receipt["billing_probe"] == {
        "attempted": True,
        "model": "text-embedding-3-large",
        "input_count": 1,
        "embedding_values_recorded": False,
        "status": "blocked",
        "http_status": 429,
        "error_type": "billing_not_active",
        "error_code": "billing_not_active",
    }
    assert "private account detail" not in serialized


def test_invalid_key_shape_fails_before_network(monkeypatch):
    monkeypatch.setattr(
        readiness.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("network should not be called"),
    )
    with pytest.raises(readiness.ReadinessError, match="invalid shape"):
        readiness.check_readiness("short", probe_billing=True)
