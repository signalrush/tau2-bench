# Tau3 Banking - GLM-5.2 Trial-0 Parity Report

Agent-owned audit of the completed 97-task single-trial run against Sierra's official four-trial GLM-5.2 submission.

| 144/388 | 33/97 | -3.0928 pp | 97/97 |
|---|---|---|---|
| Official passes | Reproduced passes | Rate delta | Valid coverage |

## NOT EXACT

### TL;DR

| Official | Reproduced | Delta | Coverage | Main attention |
|---|---|---|---|---|
| [144/388, 37.1134%](https://github.com/sierra-research/tau2-bench/blob/0f67910830d0b0168c43637de9ed0d5a355cd56c/web/leaderboard/public/submissions/glm-5-2_sierra_2026-08-04/submission.json) | [33/97, 34.0206%](https://github.com/signalrush/tau2-bench/blob/agent/tau3-banking-modal-parity/reproduction/tau3_banking/reports/glm52_trial0_metrics.json) | -3.0928 percentage points | 97/97, all `user_stop`, 0 infrastructure errors | Three official trials are missing, and official-vs-candidate traces have not been audited end to end |

The run is execution-complete and its 33/97 score is valid for the frozen single-trial contract. It is **not** an exact reproduction of the official 144/388 result: the denominator and rate differ, while route, sandbox, embedding-cache, tool-usage, and trace-rendering parity remain unresolved.

### Parity evidence

| Layer | Status | Evidence and nuance |
|---|---|---|
| Score | FAIL | Official 144/388 = 37.11340206185567%; reproduced 33/97 = 34.02061855670103%. Rate delta: -3.09278350515464 percentage points. |
| Harness | PARTIAL | Both use tau2-bench v1.0.1, 97 tasks, `alltools`, seed 300, 200 steps, and 10 consecutive errors. Official has four trials; reproduced has one and uses Modal, whose exact command-output equivalence is unproven. |
| Tools | PARTIAL | Reproduction exposes the frozen 17-tool initial schema, hash `5e2d300e...271ae1`. GLM trace-level used-tool counts, arguments, outputs, and discoverable-tool order have not been compared. |
| Model config | PARTIAL | Reproduction requested `openrouter/z-ai/glm-5.2`, temperature 1.0, top-p 1.0, 16,384 output tokens, and `xhigh` reasoning; all 2,450 assistant responses resolved through Sail Research. Official provider-route identity still needs trace-level verification. |
| Trace rendering | PARTIAL | `tau2.to_litellm_messages`, OpenAI function-tool JSON, and `tool_choice=auto`; reasoning is raw-trace-only after its turn. GLM tokenizer, Jinja template, BOS/EOS policy, and hosted renderer are not exposed or hashed. |
| Coverage | PASS | 97/97 exact task keys, 97 `user_stop` terminations, zero final infrastructure placeholders, unique response-ID receipts, and clean-runtime validation. |
| Grading | PARTIAL | Deterministic grading and reward recombination passed internal guards. Task 102 used the dated GPT-4.1 judge and its NL assertion passed, while DB failure kept reward 0. The complete official per-task component vector has not yet been compared. |
| Behavior | NOT COMPARED | [Official trajectories](https://sierra-tau-bench-public.s3.us-west-2.amazonaws.com/submissions/glm-5-2_sierra_2026-08-04/trajectories/banking_knowledge_results.json) are public, but a strict GLM official-vs-candidate message, tool, output, and reward-vector audit has not yet been published. |

**Trace boundary finding:** the checked-in renderer serializes assistant content and tool calls into the next request, but not prior `reasoning_content`; the complete provider response remains in `raw_data`. This proves the reproduction's history policy. It does not prove that Sierra's hosted endpoint applied the same tokenizer revision or private Jinja template, so that layer remains partial.

### Result and execution metrics

| Metric | Reproduced value | Scope |
|---|---:|---|
| Valid trajectories | 97/97 | One trial |
| Passed trajectories | 33 | Binary task reward |
| Assistant responses | 2,450 | GLM-5.2 through Sail Research |
| User-simulator responses | 708 | GPT-5.2 through OpenAI/default |
| Serialized cost breakdown | $21.61216452 + $1.93359775 + $0.11268 | Assistant + user simulator + judge |
| Serialized total | $23.65844227 | Excludes embeddings, Modal, and discarded attempts |

Resume retried infrastructure keys only; it never replayed or transplanted scored outputs. Thirty-six empty terminal responses and nine transient TLS failures were discarded, so their spend is absent from `results.json`.

### Exact commands

Run from `/home/tianhaowu/mono/tau3-banking` on the evaluation host. The OpenRouter credential is read from `~/.rllm/config.json`; it must never appear in argv, logs, manifests, or this report.

#### 1. Validate the route with the bound smoke

```bash
uv run --frozen --extra knowledge python \
  reproduction/tau3_banking/run_glm52.py smoke \
  --output-dir \
  reproduction/tau3_banking/runs/glm52_smoke_8904806_20260823T0415Z \
  --execute --confirm-paid-api-calls
```

The smoke must complete task 001, resolve GLM-5.2 only through Sail Research, resolve GPT-5.2 only through OpenAI, and pass route, grading, response-ID, provenance, and cost guards before a full run is accepted.

#### 2. Launch or resume the frozen 97-task run

```bash
uv run --frozen --extra knowledge python \
  reproduction/tau3_banking/run_glm52.py full \
  --output-dir \
  reproduction/tau3_banking/runs/glm52_full_8904806_20260823T0420Z \
  --smoke-manifest \
  reproduction/tau3_banking/runs/glm52_smoke_8904806_20260823T0415Z/glm52_manifest.json \
  --resume --execute --confirm-paid-api-calls
```

- Remove `--resume` only for the first launch into a new empty run directory.
- `--resume` authenticates the immutable checkpoint, skips validated keys, and retries only infrastructure or missing keys.
- `--confirm-paid-api-calls` acknowledges paid work; the credit gate is admission control, not a provider hard cap.
- Do not change the task list, smoke manifest, runtime commit, model routes, or sampling configuration within a run directory.

#### 3. Render and verify this PDF

```bash
uv run reproduction/tau3_banking/render_parity_report.py \
  reproduction/tau3_banking/reports/glm52_trial0_parity.md \
  reproduction/tau3_banking/reports/glm52_trial0_parity.pdf \
  --pages-dir \
  reproduction/tau3_banking/reports/glm52_trial0_parity-pages
```

This command checks unresolved placeholders, external URI annotations, extractable text, replacement glyphs, page count, and nonempty page images. Every rendered page must still be inspected visually.

### Links and attention

- [Official immutable submission](https://github.com/sierra-research/tau2-bench/blob/0f67910830d0b0168c43637de9ed0d5a355cd56c/web/leaderboard/public/submissions/glm-5-2_sierra_2026-08-04/submission.json), [raw official trajectories](https://sierra-tau-bench-public.s3.us-west-2.amazonaws.com/submissions/glm-5-2_sierra_2026-08-04/trajectories/banking_knowledge_results.json), and [trajectory visualizer](https://taubench.com/leaderboard/#trajectory-visualizer?model=glm-5-2_sierra_2026-08-04&domain=banking_knowledge)
- [Benchmark at the pinned upstream commit](https://github.com/sierra-research/tau2-bench/tree/fc0055dc4e0a316c3f83133267fbd6faaa770992), [official tasks](https://github.com/sierra-research/tau2-bench/tree/fc0055dc4e0a316c3f83133267fbd6faaa770992/data/tau2/domains/banking_knowledge/tasks), [tool implementation](https://github.com/sierra-research/tau2-bench/tree/fc0055dc4e0a316c3f83133267fbd6faaa770992/src/tau2/domains/banking_knowledge), and [grader](https://github.com/sierra-research/tau2-bench/tree/fc0055dc4e0a316c3f83133267fbd6faaa770992/src/tau2/evaluator)
- [GLM-5.2 endpoint](https://openrouter.ai/z-ai/glm-5.2), [runner](https://github.com/signalrush/tau2-bench/blob/agent/tau3-banking-modal-parity/reproduction/tau3_banking/run_glm52.py), [result receipt](https://github.com/signalrush/tau2-bench/blob/agent/tau3-banking-modal-parity/reproduction/tau3_banking/reports/glm52_trial0_metrics.json), [Modal receipt](https://github.com/signalrush/tau2-bench/blob/agent/tau3-banking-modal-parity/reproduction/tau3_banking/artifacts/shell_oracle_full_active_manifest.json), and [reproduction log](https://github.com/signalrush/tau2-bench/blob/agent/tau3-banking-modal-parity/reproduction/tau3_banking/REPRODUCTION_LOG.md)
- [PDF source](https://github.com/signalrush/tau2-bench/blob/agent/tau3-banking-modal-parity/reproduction/tau3_banking/reports/glm52_trial0_parity.md) and [PDF QA receipt](https://github.com/signalrush/tau2-bench/blob/agent/tau3-banking-modal-parity/reproduction/tau3_banking/reports/glm52_trial0_parity.receipt.json). Artificial Analysis's separate [27% result](https://artificialanalysis.ai/articles/glm-5-2-is-the-new-leading-open-weights-model-on-the-artificial-analysis-intelligence-index/) uses a non-comparable x5 `bm25_grep`/GPT-5.4 Mini contract.

**Attention:** three more trials are necessary but not sufficient. Exact parity also requires 144/388, matching task/trial rewards, routes, trace/tool behavior, renderer evidence, sandbox, and embedding state.

**Hashes:** result `84c89c9a0a87a5aaf0c6a16998e4333a860ae3d810c815690cf6619c96667774`; manifest `639cc89544a4aa72bf7c16c89770825cb406ed00f6f7e16e7effbaa6ee0ea942`. Remaining receipts are in the linked JSON; the 329 MB official artifact was linked, not copied.

Evaluation runtime commit `4643dc52d58538e5e897b761d6e061f2edc88a49`; final validation completed 2026-08-23 UTC.
