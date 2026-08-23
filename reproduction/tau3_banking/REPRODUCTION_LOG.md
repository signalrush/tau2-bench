# Reproduction log

## 2026-08-22 — reference reconstruction

- Identified the public leaderboard source as PR 452 and the S3 submission
  `qwen3-8-max_sierra_2026-08-04`.
- Confirmed the result records Git commit
  `fc0055dc4e0a316c3f83133267fbd6faaa770992`, release v1.0.1, domain
  `banking_knowledge`, `alltools`, seed 300, 4 trials, 200 steps, and 10 errors.
- Confirmed the four generated trial seeds directly from all 388 trajectory
  records: 626729, 373753, 361454, and 1567.
- Verified public metadata SHA-256
  `afd5525e447a221f6997b6af8a6a72536acda81b0e7775fd7124836a13a9ad76`
  (1,340 bytes) and trajectory SHA-256
  `8c8191c43dfb2d21c1322cc154740e5e6044151837ab817c2cbbcd13ffeb626e`
  (246,971,719 bytes).
- Recomputed 214 reward points across 388 simulations, exact pass@1
  `55.154639175257735%`, and 388 `user_stop` terminations. No infrastructure
  terminations were present.
- Extracted all 97 four-trial reward vectors into `reference.json`. Selected an
  exact-score gate with tasks `001,003,004,007,014,032,034,035,046,102`:
  22/40 (`55.0%`) with per-trial totals `[6,6,4,6]`. Task 102 replaces the
  cheaper task 010 so the gate covers the benchmark's only NL assertion.
- Recomputed historical provider-serialized costs: $0.14192925 for the one-task
  smoke, $8.84201230 for the 40-conversation gate ($8.33811800 agent plus
  $0.50389430 user), and $246.13332615 for all 388 chats. These figures exclude
  embeddings, NL judges, and Modal.
- Recorded immutable data/source Git objects in `reference.json`. The working
  checkout HEAD matched the official commit.

## 2026-08-22 — harness implementation

- Added an atomic reference fetcher with size and SHA-256 enforcement.
- Added a bounded JSON comparator keyed by task and trial. Score parity and
  tool behavior parity are reported separately; a missing or extra simulation
  cannot pass the score gate.
- Added dry-run-by-default smoke, 10-task subset, and full launch modes. Paid
  execution requires an explicit ceiling acknowledgement. Full execution also
  requires `ALLOW_FULL_RUN=1` and a current exact subset gate receipt.
- Added non-logging OpenRouter credential loading and explicit OpenRouter dense
  embedding transport. Pinned the GPT-5.2 user and GPT-4.1 NL judge to the
  OpenAI provider with fallback disabled. Both OpenRouter API-base environment
  names are manifest-bound and overwritten in the paid child process, so
  ambient endpoint variables cannot redirect requests. Added Modal
  backend/app/timeout environment settings.
- Preserved the official Qwen request arguments and added a free preflight that
  permits paid execution only while the exact dated Alibaba snapshot is Qwen's
  sole active OpenRouter endpoint. Endpoint manifests now retain active and
  matching counts. The committed full shell-order fixture path is set
  explicitly, so an ambient `TAU2_MODAL_ORDER_MANIFEST` cannot redirect a run.
  The wrapper's offline graders and paid children pin `TAU2_DATA_DIR`, disable
  `.env` loading, and resolve `tau2` from this checkout; paid children also
  disable user-site loading and scrub ambient Python/uv project/runtime overrides.
- No paid model, embedding, or Modal evaluation was run while building the
  harness.

## 2026-08-22 — offline harness validation

- JSON validation and `py_compile` under the locked uv runtime passed for the
  config and all eight harness scripts. Ruff lint and format checks passed.
- Submission fetch and second-pass `--verify-only` both produced the pinned
  1,340-byte SHA-256 exactly.
- Recomputed the reference config independently: 97 task files, 388 binary
  rewards, reward sum 214, exact `55.154639175257735%`, gate reward 22/40 with
  `[6,6,4,6]` trial totals, and all four Python-generated trial seeds matched.
- Strict comparison of the official 40-record gate slice against the pinned
  trajectory returned score, grading-component, and tool behavior parity.
  Gate creation now rejects `--score-only` and requires a guarded execution
  manifest, exact provider/judge routes, and strict paired ToolMessage output.
- Added an explicit known-dense-drift gate mode after proving that OpenRouter
  embedding scores cannot be byte-identical to the unrecoverable direct-OpenAI
  cache. Strict behavior diagnostics remain unchanged; the waiver classifies
  only paired assistant `KB_search_dense` ToolMessage content differences and
  requires zero missing, reordered, argument-changed, unpaired, or other tool
  mismatches. This introduced schema-v3 full gates; the later aggregate
  sampling guard supersedes them with schema v4.
- Deliberately changed one reward; the comparator exited 1 and reported the
  exact task/trial reward mismatch. Deliberately removed tool calls; it retained
  score parity but exited 1 with tool count and sequence mismatches.
- Full strict comparison of the public trajectory against itself returned
  388/388 records, reward sum 214, exact pass rate, grading components, and
  tool behavior with zero mismatches. Reproduction configuration/provenance
  validation correctly rejected that historical artifact as a new guarded run.
- Smoke and guarded-full launch plans were generated offline. The full plan had
  97 explicit task IDs, four trials, concurrency 10, and the pinned arguments.
  Full mode correctly refused without `ALLOW_FULL_RUN=1`; paid mode correctly
  refused without `--confirm-paid-api-calls`.
- The configured OpenRouter key shape, local Modal credential presence, Modal
  backend wiring, OpenRouter embedding wiring, and NL-judge environment wiring
  were checked without logging secret contents or making remote calls.
- After the aggregate-sampling, restart-safe resume, raw-cost, and full-manifest
  guards were integrated, the final offline slices passed: 67 focused harness
  and Modal tests, 13 provider-cost tests, and 457 broader banking/environment
  tests with one skip. Both shell-order generators were current, the BM25 oracle
  remained 1,910/1,910, and targeted Ruff, compilation, JSON, and diff checks
  passed. The two legacy `test_llm_utils` generation tests were deliberately not
  run because they make live OpenAI calls; their 13 cost-only siblings passed.

## 2026-08-22 — live parity evidence recorded

- Added a reproducible shell oracle over the exact gate task set. The smoke
  slice matched 6/6 unique commands exactly (report SHA-256
  `55218fe1359c61c0dc818ff3267c7aa4ca10526a2abe2a63849b71770d50e589`).
  The archive-based gate replay matched 215/263 unique commands exactly across
  275 calls (81.7490%; report SHA-256
  `ff92d2b5d24937836ca7c36cbad0d693e1c24ec54433f312b1398085dce7c597`).
  All 48 differences were classified: 47 recursive-grep traversal-order
  differences and one root `ls -la` filesystem-metadata difference.
- Derived one disclosed, uniform filesystem order from public gate trace paths
  and corpus matches. A network-blocked Modal tmpfs validation preserved all
  699 insertion positions and reproduced 59/59 recursive gate commands,
  including all 47 prior ordering mismatches. The deterministic manifest has
  451 constrained filenames, 248 lexical tie-breaks, and SHA-256
  `898b4038585ab4bd10be0ed57f396c4ae5a2b46d8e339e39cc5c8d8219e1d32f`.
  It does not inspect commands or replay output at runtime, but is explicitly a
  trace-derived reproduction fixture and is insufficient for a blind/full run.
- Checked in the deterministic 699-entry order manifest and its offline
  generator. Modal now extracts that order directly onto tmpfs and exposes it
  through the unchanged `/knowledge_base` path. The strict recursive oracle
  reproduced 59/59 commands, and the complete gate shell oracle reproduced all
  263/263 unique commands across 275 recorded calls. The latter also uses a
  narrow normalization for only the total and `.`/`..` rows of a leading bare
  `ls -la`; an explicit-path listing is never normalized.
- Corrected Modal's visible file modes to match the official Linux shell
  (`drwxrwxr-x` directories and `-rw-rw-r--` files) while retaining read-only
  enforcement through root ownership and an irreversible uid/gid 65534 drop.
  A live 698-document `ls -la` check matched file modes, names, and byte sizes;
  a write attempt returned permission denied. Filesystem allocation totals and
  the `.`/`..` metadata remain backend-specific.
- Rebuilt all 698 document embeddings with one OpenRouter route pinned to the
  OpenAI provider. The resulting cache SHA-256 is
  `2600dc04615b3a0bf01ff03dd3868bc6ba78298ca0f9aab158b93ca5f176cdc5`.
- Found that document loading order was host-filesystem dependent. The macOS
  order reproduced only 1,774/1,910 official BM25 calls; lexical loading
  reproduced all 1,910/1,910 exactly. The loader is now deterministic and the
  cache reorders existing embedding rows by document ID without a paid rebuild.
  The effective sorted cache is `(698, 3072)`, finite `float64`, with semantic
  SHA-256 `7b1668a5b9afd48edba1ef195c10b534accafb91f1da8229c91ea0c0fabb562b`.
- Compared all 1,806 official dense calls (1,802 unique queries) against that
  fresh cache: 1,188/1,806 (65.7807%) had the exact top-k order, 1,787/1,806
  (98.9480%) had the same top result, mean top-k overlap was 99.5238%, minimum
  overlap was 75%, and displayed scores were exact for 0/1,806 calls.
- The official embedding cache was not recoverable. Dense retrieval remains an
  unresolved exact-parity blocker, so no paid agent/user simulation was
  launched during this phase.
- Explored a uniform full-corpus shell order without model calls. An ephemeral
  Modal replay matched 4,581/4,614 unique commands (99.2848%) and retained
  263/263 gate-command parity. The command was
  `uv run --frozen --extra knowledge python /tmp/tau3_full_modal_oracle.py`;
  it selected the temporary manifest through `TAU2_MODAL_ORDER_MANIFEST`.
  The candidate file SHA-256 was
  `2dd6900198202d40ad466031be4b86d0fb7d699352680821f66f27e594356de2`,
  its order SHA-256 was
  `f925abd0b262c3317cedffbd1dd5d4c2a5a4495eee77e65834119ebeef7f0bf6`,
  and the report SHA-256 was
  `cc28f4bfe1a50815a91acb140f309677c34b848a738c26e5da58809fdeed8d90`.
  This is explicitly an ad-hoc exploratory measurement: neither temporary
  script nor candidate is checked in, so it is not a standalone receipt and is
  not used by the paid runner.
- Classified its 33 unique mismatches: 10 traversal-order cases, 14 historical
  `sandbox-runtime` exclamation-mark escaping cases (15 calls), four random
  historical `pwd` paths, two EROFS-versus-EACCES diagnostics, one Bash
  argv-zero diagnostic, one missing-SciPy command, and one explicit-path `ls`
  metadata difference. Changed Modal agent commands to invoke
  `/usr/bin/bash`, which fixes the authentic argv-zero difference. Deliberately
  did not rewrite commands, paths, stderr, or tool answers, and did not add
  SciPy or the exploratory order to the scored runtime.

## 2026-08-22 — official-trajectory regrade

- Regraded all 388 published trajectories against the pinned v1.0.1 tasks with
  Modal selected. Regrading created no remote Modal sandboxes; retrieval staging
  stayed local and all temporary environments were released.
- Using the moving `openrouter/openai/gpt-4.1` alias changed task 102 trial 0
  from 0 to 1 and produced 215/388. This isolated the only grading drift to the
  benchmark's sole `NL_ASSERTION` task.
- Switched the judge transport to the exact benchmark model name,
  `openrouter/openai/gpt-4.1-2025-04-14`. A four-trial task 102 probe restored
  final rewards `[0,0,0,0]`, though one non-consequential NL classification
  varied where the DB component was already zero.
- Repeated the complete 388-trajectory regrade with the dated model. It matched
  exactly: reward 214/388, pass rate `55.154639175257735%`, task 102 DB
  components `[1,0,0,0]`, NL components `[0,0,1,1]`, and final components
  `[0,0,0,0]`. This confirms the grading path while retaining the warning that
  a model judge is not guaranteed deterministic even at temperature zero. The
  retained gitignored regrade artifact SHA-256 is
  `6248bed0ad1fb5b8fcd9edeedd447ba3197d5b044ad78e5e51188bedfddd8c8e`.

## 2026-08-22 — live seed-replay diagnosis and aggregate gate

- Published the initial standalone implementation to the user fork branch
  `signalrush/tau2-bench:agent/tau3-banking-modal-parity` as commit
  `f1b1658abb0b1382703d8b686a5febf17b3ef4a3`. A fresh network clone at
  `/tmp/tau3-banking-fresh.18HRmA/repo` passed the locked offline install,
  selected-cache validation, clean-worktree check, and dry smoke without making
  remote calls.
- Launched the first paid smoke with
  `uv run --frozen --extra knowledge python reproduction/tau3_banking/run.py smoke --output-dir reproduction/tau3_banking/runs/gate_trial0 --execute --confirm-paid-api-calls --cost-ceiling-usd 0.25`.
  It produced candidate artifact SHA-256
  `7e594d1f98a9c98cb3d4566549034d6dcbf186904c9526e64696d04de410f764`
  and guarded execution-manifest SHA-256
  `48c41e14193aebb8a9309818ad8eceb1e9935de22a90ecd7f83261c825d8c516`.
- The first paid smoke completed task 001 trial 0 with reward 1, but diverged
  from the published trajectory despite the same seed 626729 and identical
  committed prompts, tools, model arguments, and provider pins.
- Repeated only the first hosted-model requests to isolate sampling. GPT-5.2
  first-user content changed from SHA-256
  `ee51d33b867b92ab172bf8d20e9e8491b767aebf0948b04ad9cd96250a4607be`
  (`gen-1787393465-q38LkKjXJYijmvoTfpYQ`) to
  `1296078c1a996c6291887cf3bfefc046de6612604b657486ead2036a73ef55df`
  (`gen-1787393683-avNYfrT0HhPS0BpykrQ5`), both OpenAI/default. The official
  first-user content SHA-256 is
  `c8bcae567670de2c5c2e4daf0446515c42e0f001f40654622f601c6bc84abf40`.
- Qwen's canonical initial tool call changed from SHA-256
  `80458bfe976f892288e8de50e374fe2e6930cee38419cbff00a4cc0d9d5f4a58`
  (`gen-1787393466-MJM6SNmXOPdQInO9Mvd8`) to
  `489768bcc9eeb8de59fa7582f7a15ac3cb92162f76a26bbb9eff65dac7fd8a0d`
  (`gen-1787393717-LrzM8u8Ls8RMJKyUoNQK`), both Alibaba with null service
  tier. This proves that hosted seed replay is not trajectory deterministic.
- Added an explicit aggregate-only model-sampling gate. Strict per-record
  reward/component, text, call, argument, and output diagnostics are retained.
  When explicitly requested, their sampling-attributable differences may be
  waived only while all 40 task/trial keys, seeds, `user_stop` terminations,
  internally recombinable binary grading, configuration, routes,
  manifest/runtime state, and the exact 22/40 aggregate match. Identical
  non-dense calls with different output remain unwaivable backend drift; the
  separate dense waiver still applies only to identical dense calls.
- Hardened that gate before expanding the paid subset: tool results are aligned
  by exact role/name/arguments across call insertion and reordering, with
  ambiguous duplicate results rejected; reward breakdowns are recomputed from
  canonical DB/action/environment/NL/communication evaluator records; and null
  raw user models are rejected. Each differing deterministic component is now
  recomputed with the authoritative task and official local evaluator in a
  retrieval-free environment, so failed/no-op writes and generic/discoverable
  state mutations receive their exact semantics rather than name-based credit.
  NL outcome drift always requires task 102's validated dated judge route, and
  the full gate requires an exact zero-issue attribution receipt. The paid
  endpoint preflight now requires the same exact GPT-5.2 alias inventory proof
  (4 active total, 3 OpenAI-eligible, all 3 matching the dated snapshot) as the
  comparator.
- Added the ten-task trial-0 intermediate (6/10, historical chat cost
  $2.59890095) before the 40-simulation gate. It can resume the smoke, and the
  full subset can resume it. A partially completed four-trial expansion can
  also resume despite upstream retaining stale `num_trials=1` metadata; exact
  task/trial/seed and bound checkpoint-manifest provenance checks remain.
- The smoke's raw OpenRouter usage costs were $0.154672 agent and $0.0082551
  user, $0.1629271 total. The comparator now reports these non-gating raw
  totals because LiteLLM's mapped top-level agent cost may be zero.
- OpenRouter serialized the user model as `openai/gpt-5.2`. This moving alias
  is accepted only when the bound valid manifest contains the exact catalog
  proof for provider OpenAI and resolved endpoint
  `openai/gpt-5.2-20251211` with four active and three matching endpoints.
  Full-gate verification revalidates the route counters and catalog proof.

## 2026-08-22 — deterministic full-corpus Modal fixture

- Added `generate_full_shell_order.py` and a checked-in 699-entry uniform
  filesystem order derived from the pinned 5,135 recorded shell calls (4,614
  unique commands). The generator treats all 767 subset edges as hard
  constraints, admits only acyclic full-trace edges, and handles compound
  commands conservatively: 54 had a unique segmentation, 31 retained only
  edges safe under every valid segmentation, and one was unsegmentable.
- The resulting fixture has 7,548 precedence edges, constrains 698/699 files,
  and uses the subset order to break the final tie. Its order SHA-256 is
  `ddb11f1a583e408079c136805c786f6e53903afb3dad46047c69a06b3b01b6f3`;
  the manifest file SHA-256 is
  `5f8005d162f81d9eadf6836b296d4a334090daec60c0228770e8b8de890d37f8`.
- Verified the generated fixture offline with
  `uv run --frozen --extra knowledge python reproduction/tau3_banking/generate_full_shell_order.py --check`.
  Then replayed the fixed subset against one live network-blocked Modal sandbox
  with
  `TAU2_MODAL_ORDER_MANIFEST=reproduction/tau3_banking/full_shell_order_manifest.json uv run --frozen --extra knowledge python reproduction/tau3_banking/compare_shell_oracle.py --mode subset --scope all --execute --output reproduction/tau3_banking/artifacts/shell_oracle_subset_full_manifest.json`.
  The result was 263/263 unique commands exact across 275 recorded calls, zero
  mismatches, applied order SHA-256 `ddb11f1a...b01b6f3`, and report SHA-256
  `626fa9d613ec8d789a258bc81d686358b23b2a07131da98b21df841009c7a1bf`.
- Switched the Modal manager default and guarded runner environment to this
  single full fixture for smoke, trial-0, subset, and full runs. Runtime order
  selection remains command-independent and no recorded output is replayed.
- Made abrupt-termination resume provenance crash-safe. A `running` manifest may
  authorize the structurally validated checkpoint produced by that exact
  guarded launch; resumed launches additionally bind the already validated
  pre-run checkpoint SHA-256. Finalized manifests retain exact post-run state
  and checkpoint digest requirements.
  Paid `uv` children inherit the output-directory OS lock, preventing a second
  resume from writing or spending concurrently even if the Python wrapper is
  killed first. Fresh-run absence and resume checkpoint/state provenance are
  rechecked after acquiring the lease and before prewarm or paid launch.
  Successful runs with a transient finalization fingerprint error retain the
  original zero runner exit code and can be recovered only by fresh exact
  checkpoint and clean-state validation.
- Made the full live Modal shell-oracle receipt a hard full-run prerequisite.
  The guard binds its path, SHA-256, official-reference and order-fixture
  digests, complete counts/details, and committed score-impact review. Any
  remaining difference is treated as potentially behavior/score affecting;
  reviewed and explicitly accepted nonzero drift additionally requires
  `--allow-known-full-shell-drift`, which is persisted in the run manifest.
- Added official-schema and half-duplex chronology validation for every
  trajectory. Tool results must follow their pending call with matching ID and
  requestor, participant turns must be valid, call IDs must be unique, and
  repeated stateful call outcomes retain occurrence order. These failures are
  structural/non-waivable. Judge response IDs are also globally disjoint from
  participant generation IDs.

## 2026-08-22 — active full Modal shell receipt

- Ran the final no-model, 4,614-unique-command oracle against the active fixture
  and hydrated Modal image with the exact command:

  ```bash
  env -u TAU2_MODAL_EXPECTED_IMAGE_ID \
  TAU2_MODAL_ORDER_MANIFEST=reproduction/tau3_banking/full_shell_order_manifest.json \
  uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/compare_shell_oracle.py \
    --mode full --scope all --execute --max-details 100 \
    --output reproduction/tau3_banking/artifacts/shell_oracle_full_active_manifest.json
  ```

  The tracked receipt SHA-256 is
  `17728b8c8ae721e23506a06bd7dfe9a276009222ab17f9af0ada20ace9fd06eb`.
  It binds image-recipe SHA-256
  `fa738d7f079e0b3cfccf0c7e30f140064409afd04732eb3f5182f737f7126795`
  and hydrated Modal image object ID `im-57yaJoNct9YREpBb74YQ0k`.
- The final result is 4,603/4,614 unique commands exact
  (`99.76159514521024%`) and 5,124/5,135 recorded occurrences exact
  (`99.78578383641675%`). All 11 mismatch details are retained, spanning 11
  task/trial records across 10 tasks and zero gate-subset simulations.
- The 11 residuals are three traversal-order differences (tasks 080/0, 023/1,
  and 070/2), four unrecoverable randomized historical working-directory paths
  (067/0, 063/1, 076/2, and 044/3), two EROFS-versus-EACCES diagnostics (019/0
  and 022/3), one explicit-path `ls` ownership/timestamp difference (044/2),
  and one remaining `srt` conditional-shell difference (064/2).
- The compatibility transform mirrors `sandbox-runtime` 0.0.23 by replacing
  each command-argv `!` with `\!`. A targeted 20-command probe matched 17/20
  historical outputs after this transform; the active receipt retains the one
  remaining full-corpus conditional-shell mismatch rather than spoofing it.
- The Modal image pins the exact install call
  `modal.Image.debian_slim().pip_install("scipy==1.16.3")`. This restores the
  official task 095 trial 2 command whose executable core is:

  ```bash
  python3 - <<'EOF'
  from scipy.optimize import brentq
  bal = 95550.0
  days = 31
  def i(apy): return bal * ((1 + apy) ** (days / 365) - 1)
  ap = brentq(lambda a: i(a) - 450, 0.01, 0.2)
  print("APY that yields $450:", round(ap, 5), f"{ap * 100:.3f}%")
  EOF
  ```

  This is the same numerical operation as the recorded command; formatting-only
  list output omitted here does not alter the executed fixture or receipt.
- Cleanup completed with zero live Modal tasks. The receipt and guard describe
  the residuals honestly: all 11 can change model-visible output, downstream
  behavior, and score. They are explicitly accepted only after an exact 22/40
  live subset and only with `--allow-known-full-shell-drift`; this authorizes a
  distribution-level Modal reproduction, not exact trajectory parity.

## 2026-08-22 — fork publication and fresh-clone receipt

- Published the hardened standalone banking harness to
  `signalrush/tau2-bench`, branch `agent/tau3-banking-modal-parity`, at commit
  `16c5a7661f48a2b4c333105d0a46937c424843d4`. The scoped commit contains
  exactly 19 intended files and no credential-like literals; its parent is the
  initial Modal harness commit `f1b1658abb0b1382703d8b686a5febf17b3ef4a3`.
- Before publication, ran the complete offline regression command over the
  harness, Modal manager/lifecycle, cost, and NL-judge tests: 138 passed and the
  two intentionally live-model tests were deselected. Ruff check, Ruff format
  check, `git diff --cached --check`, receipt/fixture digests, and the full-order
  generator check all passed.
- Cloned that exact fork branch into a new temporary directory and ran:

  ```bash
  uv sync --frozen --extra knowledge
  uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/fetch_reference.py --artifact all
  uv run --offline --frozen --extra knowledge python \
    reproduction/tau3_banking/fetch_reference.py --artifact all --verify-only
  uv run --offline --frozen --extra knowledge python \
    reproduction/tau3_banking/generate_full_shell_order.py --check
  uv run --offline --frozen --extra knowledge python \
    reproduction/tau3_banking/run.py smoke
  ```

  Dependency sync installed the pinned lock, the public submission and
  236-MiB trajectory both passed their committed SHA-256 checks, the generated
  full order was current, and the dry smoke emitted the exact guarded argv and
  environment without reading a key or making model, embedding, or Modal
  calls. `git status --porcelain` remained empty and the clone HEAD equaled the
  published commit.

## Open parity risks before any full run

1. The official GPT-5.2 user, GPT-4.1 judge, and `text-embedding-3-large` calls
   used direct OpenAI; reproduction must use OpenRouter. Live dense comparison
   is not exact and the official cache is unavailable.
2. Modal replaces the historical local Anthropic `sandbox-runtime`. The active
   disclosed full-trace fixture preserves all 263/263 unique subset shell
   commands (275 recorded calls), including the strict 59/59 recursive slice.
   It is trace-derived and constrains 698/699 files. The earlier ad-hoc
   full-corpus probe reached 4,581/4,614 unique commands with a different order.
   The pinned active-fixture receipt reaches 4,603/4,614; its 11 model-visible
   differences remain potentially behavior/score affecting and require the
   explicit full-run acknowledgement described above.
3. GPT aliases may have moved since 2026-08-03. Qwen paid execution is blocked
   unless its sole active endpoint remains the exact Alibaba snapshot; still
   confirm raw response provider/model fields in smoke output before the subset.
4. The official result does not serialize concurrency. Ten was reconstructed
   from launch overlap; it is not a signed metadata field.

## 2026-08-22 — fail-closed credit and checkpoint validation

- A final paid smoke attempt reached OpenRouter but received HTTP 402 for
  insufficient credit. Upstream `tau2 run` nevertheless exited zero after
  serializing one `infrastructure_error` simulation, and the wrapper initially
  treated that process exit as completion. The exact command was:

  ```bash
  uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/run.py smoke \
    --output-dir reproduction/tau3_banking/runs/parity_b5480c1 \
    --execute --confirm-paid-api-calls --cost-ceiling-usd 0.25
  ```

  The resulting checkpoint SHA-256 is
  `88ab27ca094323160596533c43129f6a9e6f2afbb2da9f10508ef5c9e48c4410`;
  it contains exactly one infrastructure-error record, no generated model
  response, and no model usage cost. No benchmark result was claimed.
- Paid execution now performs an authenticated `GET /api/v1/credits` with the
  authoritative file credential before it creates the output directory or
  starts cache, model, or Modal children. Both returned totals must be finite
  and nonnegative, and their difference must cover the selected mode's full
  historical chat cost. Unavailable, malformed, or insufficient state fails
  closed. The ignored run manifest stores only the numeric allowlist and check
  time, never the key, raw response, headers, or response labels; no current
  balance is committed here.
- A zero upstream exit is now accepted only after exact task-by-trial coverage,
  zero infrastructure errors, and the pre-existing structural, grading,
  provider, response-ID, cost, and judge-route validators all pass. Failure is
  finalized as `post_run_validation_failed` with wrapper exit 2. A guarded
  resume may retain infrastructure-error records only because upstream removes
  those records and retries exactly their task/trial keys; already validated
  `user_stop` simulations remain preserved.
- Published these guards at
  `f3c10b6c49cd464f73938bb07a7d08eb3d60d847`, then ran this live no-model
  preflight against a deliberately new output path:

  ```bash
  uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/run.py smoke \
    --output-dir reproduction/tau3_banking/runs/credit_guard_probe_f3c10b6 \
    --execute --confirm-paid-api-calls --cost-ceiling-usd 0.25
  ```

  It returned wrapper exit 2 for insufficient OpenRouter credit, created no
  output directory, and launched no benchmark child. The current balance is
  intentionally not committed. A fresh clone of the published commit also
  emitted the exact guarded dry plan from a clean worktree.

## 2026-08-22 — paid smoke and 10-task trial-0 gate

- After the guarded credit check became sufficient, verified that branch
  `agent/tau3-banking-modal-parity` was clean and that the fork contained exact
  HEAD `48a92ecf69bebd2d6eae37a54c98c929e39ff85b`. Started a new run directory
  bound to that commit with:

  ```bash
  uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/run.py smoke \
    --output-dir reproduction/tau3_banking/runs/parity_48a92ec \
    --execute --confirm-paid-api-calls --cost-ceiling-usd 0.25
  ```

  Smoke completed `task_001` trial 0 with `user_stop`, reward 1, exact DB and
  action grading, zero infrastructure errors, and valid Qwen/Alibaba and
  GPT-5.2/OpenAI route receipts. Raw chat cost was `$0.32992025` (agent
  `$0.318456`, user `$0.01146425`), `2.32454x` the historical `$0.14192925`.
  Strict behavior was not identical: 22 tool calls versus the official 9 and
  37 tool-call/output mismatches, all causally classified as model-sampling
  drift; combined scoped waivers left zero residuals. The immutable smoke
  comparison SHA-256 is
  `6fb7fc6d8f356413f18f2b0ed3c8b716c5fdbe6872eb1110e18282b0d774ebd9`.

- Resumed the same checkpoint into the documented ten-task trial-0 gate:

  ```bash
  uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/run.py subset_trial0 \
    --output-dir reproduction/tau3_banking/runs/parity_48a92ec \
    --resume --execute --confirm-paid-api-calls --cost-ceiling-usd 3.5
  ```

  It completed all 10 simulations with `user_stop`, no infrastructure errors,
  and exact aggregate `6/10 = 60%`. Raw agent/user chat cost was `$3.25845055`
  (agent `$3.11104`, user `$0.14741055`); the task-102 dated GPT-4.1 judge cost
  was `$0.111872`. Task-level rewards swapped on task 014 (`0 -> 1`) and task
  034 (`1 -> 0`). Task 102 retained final reward 0 but recombined from official
  `DB=1, NL=0` to live `DB=0, NL=1`; both trajectories and every differing
  deterministic component reproduced exactly under the offline evaluator, and
  the NL change used the dated OpenAI judge route.

  The initial comparison found two conservative residuals after otherwise
  validating aggregate score, configuration, runtime/manifest, structure,
  grading, participant routes, response IDs, and judge provenance. Both were
  the unexecuted task-034 transfer-request outputs `#7` and `#8`: the candidate
  stopped after the exact ordered stateful prefix `#1` through `#6`, while the
  comparator treated the missing reference suffix as ambiguous. The comparator
  now classifies only an expected-side missing suffix after an exact observed
  prefix as downstream model-sampling drift. Candidate-added, middle-missing,
  reordered, content-changed, requestor-changed, and error-changed duplicate
  outputs remain fatal. Two regression tests cover the accepted suffix and
  rejected middle gap; the full focused harness file passes 90 tests.

  After that fix, all 363 tool-call/output mismatches are attributed to the
  disclosed sampling scope, zero behavior mismatches remain outside the waiver,
  grading integrity and score attribution are valid, and the exact trial-0
  aggregate remains 6/10. Checkpoint SHA-256 is
  `5849608ebd33dacf0f3eb969bdc842717f0adb3ec23724e48738c8b7d6ae20d2`;
  completed execution-manifest SHA-256 is
  `5353c9b7eefc1fe7f61e4b98aba2166c82c9e226607710f4b4b8a18097a4c7ea`;
  detailed post-fix comparison SHA-256 is
  `a8455566b0dd37f9341a313ab6c553bfe78e3b9f765e508aee67cc2f4c14862e`.

## 2026-08-22 — 40-run subset mismatch and full-run refusal

- Preserved the exact trial-0 checkpoint and its original clean commit by
  temporarily shelving only the audited comparator/log/test patch, then ran:

  ```bash
  uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/run.py subset \
    --output-dir reproduction/tau3_banking/runs/parity_48a92ec \
    --resume --execute --confirm-paid-api-calls --cost-ceiling-usd 12
  ```

  The credit preflight was sufficient, the runner retained the existing ten
  keys, and all remaining 30 predeclared task/trial keys completed. The full
  checkpoint contains exactly 40 `user_stop` trajectories, zero infrastructure
  errors, 701 unique participant response IDs (471 Qwen assistant and 230
  GPT-5.2 user responses), valid dated task-102 judge provenance for every
  trial, and a passing post-run structural/grading/provider validation receipt.
  The checkpoint SHA-256 is
  `85a62d20e497a163bb7a2bc63ee5441eed1ef21931872619ce579ee09154f204`;
  execution-manifest SHA-256 is
  `7933b8553fa7d63c9dbe36efef2241044571dc3063bd04082b735eba047f8170`.

- The live aggregate was **26/40 = 65%**, not the required **22/40 = 55%**.
  Live rewards by trial were `[6, 7, 7, 6]` versus official `[6, 6, 4, 6]`.
  Ten binary outcomes flipped:

  ```text
  task_001 trial 2: 0 -> 1
  task_003 trial 2: 1 -> 0
  task_007 trial 2: 0 -> 1
  task_014 trial 0: 0 -> 1
  task_014 trial 1: 0 -> 1
  task_014 trial 3: 1 -> 0
  task_032 trial 2: 0 -> 1
  task_034 trial 0: 1 -> 0
  task_034 trial 2: 0 -> 1
  task_034 trial 3: 0 -> 1
  ```

  Net task-level differences were `+1` for tasks 001, 007, 014, 032, and 034;
  `-1` for task 003; and zero for tasks 004, 035, 046, and 102. Every changed
  deterministic DB/ACTION component reproduced from its own trajectory under
  the pinned offline evaluator; grading-integrity and causal-attribution issue
  counts were both zero. This rules out scalar-grader or stale-component drift.

- Raw agent/user chat cost was `$11.92734985` (agent `$11.461118`, user
  `$0.46623185`), `1.349x` the historical `$8.8420123`; four dated GPT-4.1
  judge calls added `$0.442644`. Dense embeddings were served from the pinned
  cache and Modal cost is not serialized. The 40 conversation durations sum to
  8,224.31 seconds; concurrent wall time was about 19.6 minutes.

- The detailed offline comparator reported exact configuration, runtime and
  execution-manifest state, schema/protocol structure, raw Alibaba/OpenAI
  participant routes, unique response-ID binding, dated judge routes, and
  grading integrity. Strict trajectories nevertheless had 319 generated-text
  divergences and 1,347 tool-behavior mismatches: 237 argument, 37 count, 40
  sequence, 469 missing-output, 562 unexpected-output, one known dense-output,
  and one other same-call output difference. Of these, 1,343 are attributable
  to model-selected sampling changes and one is the separately disclosed dense
  drift. Three deliberately unwaived stateful-output diagnostics remain:
  candidate-added task-034 trial-2 transfer output, candidate-added task-102
  trial-3 referral read, and a task-102 trial-2 referral read after divergent
  referral writes. They do not explain the scalar mismatch; they keep the trace
  gate conservative. Detailed comparison SHA-256 is
  `894394be905fd49fcc3b7209861f5863778702354a11ec2bf7aebece987d06bc`.

- Transport and sampling evidence explains why identical seeds do not recreate
  trajectories. Every first GPT-5.2 request recorded exactly 81 fewer prompt
  tokens through OpenRouter than the official direct-OpenAI request; only 10/40
  first user messages were byte-identical. On those same ten trajectories, the
  first Qwen prompt-token count was exactly equal to the official trace, but
  all ten first Qwen tool calls still differed despite the same Alibaba route,
  model snapshot, seed, policy, task, tools, and xhigh-only arguments. Across
  all 40 records, zero first Qwen generations were fully identical. The excess
  score is therefore consistent with remote seeded sampling/transport drift,
  not a harness configuration, route, Modal, or grader mismatch.

- Finally attempted the documented gate write with both narrowly disclosed
  waivers:

  ```bash
  uv run --offline --frozen --extra knowledge python \
    reproduction/tau3_banking/compare_results.py \
    reproduction/tau3_banking/runs/parity_48a92ec/results.json \
    --mode subset --max-mismatch-details 2000 \
    --output reproduction/tau3_banking/runs/parity_48a92ec/subset_gate_attempt.json \
    --write-gate reproduction/tau3_banking/.state/subset_score_parity.json \
    --allow-known-dense-drift --allow-model-sampling-drift \
    --reference-results \
      reproduction/tau3_banking/artifacts/banking_knowledge_results.json
  ```

  It failed closed with exit 2 because aggregate sampling mode still requires
  the exact official reward sum. No gate file was written, and no full run was
  launched. Replaying, replacing, or cherry-picking failed keys would invalidate
  the fixed subset experiment and is intentionally not used. The 40-run
  checkpoint, three execution manifests, smoke/trial-0 comparisons, and detailed
  subset comparison are force-tracked as immutable receipts even though the
  general `runs/` directory remains ignored.

## 2026-08-22 — Nemotron 3 Super exploratory smoke

- Verified the live paid OpenRouter route for the real
  `nvidia/nemotron-3-super-120b-a12b`. The selected endpoint was BF16
  DeepInfra with a 262,144-token context, 16,384-token completion ceiling,
  seed/tool support, and fallback disabled. The agent request used medium
  reasoning (the highest explicitly supported effort), `temperature=1.0`,
  `top_p=0.95`, and `max_tokens=16000`. The GPT-5.2 user simulator retained
  low reasoning, OpenAI-only routing, and fallback disabled.

- The guarded credit check reported `$929.9503964839969` available before the
  call. A one-task diagnostic was launched from clean published commit
  `e9a1d560f97a4a6381c24f9ae23cff9357a929e8`, with task `task_001`, seed
  `626729`, concurrency one, alltools retrieval, and the pinned Modal image and
  full shell-order fixture. This diagnostic predated the standalone runner and
  is evidence only; the scored full run will use a new same-commit canonical
  runner smoke.

- Outcome: reward `1/1`, correct Gold Rewards Card application, DB/action
  checks exact, `user_stop`, duration `242.79228062502807` seconds. All 26
  generated agent responses were `nvidia/nemotron-3-super-120b-a12b` through
  DeepInfra; all three generated user responses were `openai/gpt-5.2` through
  OpenAI with default service tier. All 29 response IDs were unique. Serialized
  chat cost was `$0.079370495` (`$0.069426295` agent and `$0.0099442` user).

- Result SHA-256:
  `28e319cf7cd5e475d54a1e2dddc8787303746666453c132890745802d48ba44d`.
  Diagnostic manifest SHA-256:
  `ad9bb8272588ce213c13e2ca0ebee722a074ec61c5438a9362468ac16a611c91`.

## 2026-08-22 — Linux takeover, 81-token root cause, and direct-OpenAI transport

- Took over the reproduction on the Linux/WSL2 host from a fresh clone of the
  published fork branch. Verified the `~/.rllm/config.json:api_keys.openrouter`
  credential (same account the prior session used; sufficient credit), the
  active `rllm-project` Modal profile, and the fetched reference artifacts.
- Root-caused the constant 81-token first-request delta recorded for every
  gate task. All 40 official first GPT-5.2 user requests bill exactly 81 more
  prompt tokens than byte-identical requests through OpenRouter. Evidence:
  - OpenRouter's `cost_details.upstream_inference_prompt_cost` divided by the
    catalog prompt price reproduces the reported prompt token count exactly
    (972.0 for task_001), so the delta is real billed content, not accounting.
  - The official artifact's simulation guidelines, task JSON, greeting, and
    persona are byte-identical to the pinned v1.0.1 data, and a tiktoken
    reconstruction of the system prompt and greeting accounts for the request
    to the token per toolset; the residual overhead depends only on the task's
    user toolset and differs by exactly 81 for every distinct toolset. This
    isolates the delta to the fixed, schema-independent Chat Completions tool
    harness that direct OpenAI includes and OpenRouter's upstream forwarding
    omits.
  - A local mock-server capture proved litellm 1.81.11 sends byte-equivalent
    request bodies for `gpt-5.2` (direct) and `openrouter/openai/gpt-5.2`, so
    the difference is created server-side at OpenRouter.
  - Paid micro-probes (~$0.01): replaying the exact task_001 first request via
    OpenRouter with `parallel_tool_calls` passthrough returned the same 972
    tokens, and `provider.require_parameters` rejected the parameter outright
    ("No endpoints found that can handle the requested parameters"), proving
    no OpenRouter parameter can restore the official framing.
  - The official user simulator emitted parallel tool calls 16 times across
    388 simulations, behavior the OpenRouter framing does not expose. Under
    the official per-task reward vectors, the observed live subset excess
    (26/40 vs 22/40) sits at the 94.5th percentile (P(sum >= 26) = 5.54%), so
    a cooperative-user bias from the missing harness is a plausible mechanism
    and the transport difference is not ignorable.
- Switched the pinned reproduction transport for the GPT-5.2 user simulator,
  dated GPT-4.1 NL judge, and dense embeddings to direct OpenAI (the official
  transport), keeping the Qwen agent on OpenRouter exactly as the official
  run did. The user model is pinned to the official-resolved dated snapshot
  `gpt-5.2-2025-12-11`. reference.json records the superseded OpenRouter
  transport block verbatim with the reason. run.py now loads a second
  authoritative credential from `~/.rllm/config.json:api_keys.openai` with the
  same ambient-match policy, pins `OPENAI_BASE_URL=https://api.openai.com/v1`
  in the manifest and paid child, and adds a free dated-snapshot catalog
  preflight for both pinned OpenAI models. The GPT-5.2 moving-alias catalog
  proof machinery was removed with the transport that required it; the
  comparator now requires the direct raw shape (dated response model, no
  OpenRouter provider field, `chatcmpl-` response-ID prefix, service tier
  `default`) for user and judge responses, keeps OpenRouter `usage.cost`
  binding for the agent, and binds the serialized litellm message cost for
  direct-OpenAI responses, which is exactly the shape the official artifact
  records.
- The direct-OpenAI document-embedding cache is intentionally unpinned:
  `state_fingerprint.py` fails closed with the observed semantic SHA-256 until
  the one-time direct cache build is reviewed and pinned. The prior
  OpenRouter cache pin is retained as a provenance comment.
- Regenerated the full 4,614-command Modal shell-oracle receipt in the
  `rllm-project` workspace: 4,603/4,614 unique commands exact across 5,135
  recorded calls with the same 11 reviewed residuals, byte-identical to the
  prior workspace's details, from the same image recipe SHA-256
  `fa738d7f079e0b3cfccf0c7e30f140064409afd04732eb3f5182f737f7126795` hydrated
  as the new image object `im-tnDKIdJXoHwMlRrrDMB8FX`. reference.json rebinds
  the image object ID and the new receipt SHA-256
  `c2fb4c7612348d40391aeb7ebb8b783046c2183c166efbb755954f2661678c1a`; the
  cheap strict slice also reproduced 59/59 recursive gate commands here.
- The focused offline harness suite passes 90 tests after the transport
  rewrite; the banking-domain offline regression selection passes end to end,
  and Ruff check/format are clean. The offline dry smoke emits the direct
  argv: `--user-llm gpt-5.2-2025-12-11 --user-llm-args
  '{"reasoning_effort":"low"}'` with `TAU2_NL_ASSERTIONS_MODEL=
  gpt-4.1-2025-04-14`.
- Next steps require a billing-active `api_keys.openai` credential: build and
  pin the direct embedding cache, record a fresh dense comparison against the
  official trajectory, then restart the paid progression (smoke, trial-0,
  subset gate at exactly 22/40, acknowledged full run) in a new run directory
  bound to the new clean commit.

## 2026-08-22 — OpenRouter transport reinstated by owner decision

- The owner directed that all GPT-5.2/GPT-4.1/embedding access continue to use
  the OpenRouter credential; no direct-OpenAI key will be provided. The
  direct-OpenAI transport switch from the previous entry is therefore
  reverted: run.py, compare_results.py, state_fingerprint.py, the harness
  tests, and the transport block of reference.json are restored to their
  validated states from commit f1bfcd1 (the exact code that produced the live
  smoke, trial-0, and 40-run subset receipts). The 81-token root-cause
  analysis remains fully documented above and stands as accepted, explicitly
  disclosed non-parity: the OpenRouter user transport provably lacks the
  official request's constant 81-token Chat Completions tool-harness framing
  and the parallel tool-call capability the official user simulator exercised
  16 times in 388 simulations.
- Retained from the intervening work: the Modal image rebind to this
  workspace's content-identical rebuild `im-tnDKIdJXoHwMlRrrDMB8FX` (same
  recipe SHA-256, all 11 full-oracle residuals byte-identical) and the
  regenerated full shell-oracle receipt with SHA-256
  `c2fb4c7612348d40391aeb7ebb8b783046c2183c166efbb755954f2661678c1a`.
- Consequence recorded for the aggregate-score gate: under the official
  per-task reward vectors, the one completed live subset's 26/40 sits at the
  94.5th percentile. If the accepted transport difference biases the user
  simulator upward, the exact 22/40 gate may be systematically hard to reach;
  each fresh subset attempt is an independent ~$12.40 sample of that
  distribution. This is a knowing acceptance, not an unexplained residual.

## 2026-08-22 — exact 22/40 subset, endogenous-drift replay proof, gate provenance

- Restarted the staged progression at clean commit
  `aa6eaa5cffadb6f7f470b2235caa543d998e6e01` in a fresh run directory
  `runs/parity_aa6eaa5`. Paid smoke reproduced task_001 trial 0 with reward 1,
  `user_stop`, exact routes, and raw chat cost `$0.1843701`. The ten-task
  trial-0 intermediate completed 10/10 `user_stop` with aggregate 7/10 versus
  the official 6/10 (task_014, official vector 0011, passed trial 0); all 338
  behavior diffs were sampling-attributed with zero dense residuals.
- Resumed into the 40-run subset. All 40 simulations completed `user_stop`
  with zero infrastructure errors and aggregate **exactly 22/40**, matching
  the official 55.0%. Trial sums were `[7,4,6,5]` versus official `[6,6,4,6]`
  (aggregate-waiver scope). Raw agent/user chat cost for the full directory
  was `$11.85` with 676 unique participant response IDs; configuration,
  structural, raw-route, judge-route, execution-manifest, grading-integrity,
  and zero-issue sampling-attribution checks all passed.
- The gate write initially refused: 2 of 1,364 behavior mismatches fell
  outside both waiver scopes, both task_102 `get_referrals_by_user` stateful
  reads — one same-call output difference after divergent sampled
  `submit_referral` writes, one candidate-added duplicate read with no
  matching official outcome. These are the same conservative classes the
  previous session documented. The comparator now proves endogenous state
  divergence exactly: a residual stateful-output mismatch is attributed to
  the model-sampling scope only when the official `no_knowledge` environment
  replay of the owning trajectory's own call history reproduces the observed
  output byte-exactly (both sides for same-call pairs, the owning side for
  ambiguous duplicates; reads evaluated on a deep copy at their exact
  position). Retrieval and shell outputs are never re-derivable this way and
  stay fatal, as do failed replays. Committed as
  `2422f71` with four focused regression tests.
- The gate write then refused because the candidate's commit trailed the
  fixed comparator's HEAD. Added explicit dual-commit gate provenance:
  a gate may be written from a newer HEAD only when the candidate commit is
  its ancestor and every changed path since is inside the evaluation-only
  allowlist (harness run/compare code, tests, docs) — the checkpoint's
  production runtime (`src/tau2`, `data/`, reference config, fixtures, state
  fingerprinting) must be exactly the candidate commit. The gate binds both
  commits and the changed-path list; full-gate verification recomputes the
  same proof from the bound checkpoint and requires the manifest's post-run
  runtime head to equal the candidate commit with an unchanged embedding
  cache. Anything else fails closed.
- Separately, the guarded Nemotron 3 Super evaluation launched at the same
  commit: its smoke initially failed on a transient DeepInfra
  `engine_overloaded` shared-pool 429 (recorded as an infrastructure error
  and retried under the same manifest), then completed with reward 1/1 and
  the pinned BF16 DeepInfra/OpenAI routes; the bound 97-by-2 full run is in
  progress.

## 2026-08-22 — owner-directed single-trial full scope

- After the type-scope and manifest-provenance fixes, the subset gate was
  rewritten and the four-trial full run launched cleanly at `6c4aa41` into
  `runs/full_6c4aa41`. The owner then directed a cost reduction to a
  single-trial full evaluation, and the run was interrupted by SIGINT after
  18 completed simulations (~$6.71 raw chat cost); its manifest finalized as
  `failed` and the directory is retained as a receipt.
- `modes.full` now covers all 97 tasks for trial 0 only (derived seed
  626729): expected coverage 97, expected reward sum exactly **54/97**
  (`55.6701%`, the official trial-0 slice), credit requirement one quarter of
  the recorded four-trial chat cost. The published `214/388` remains the
  four-trial figure and is no longer this mode's live target.
- Gate provenance handles the config change narrowly: a committed
  `reference.json` delta is evaluation-only when the parsed configs differ
  ONLY inside `modes.full` (compared from the committed blobs), and a bound
  manifest's recorded config digest is accepted when it hashes the exact
  committed blob at that manifest's own runtime head under the same
  full-mode-only proof. Every other config delta still fails closed.
- The concurrent Nemotron 97-by-2 full pass ended with mass retryable
  DeepInfra `engine_overloaded` infrastructure errors; spaced resume passes
  will retry only those records.

## 2026-08-22 — single-trial full result 41/97 and failure analysis

- The single-trial full run at `c3887fe` completed 97/97 simulations with
  `user_stop`, zero infrastructure errors, exact Alibaba routes for all 2,283
  agent responses and OpenAI routes for all 704 user responses, grading
  integrity clean, and raw chat cost `$68.33`. The aggregate was **41/97
  (42.27%)** against the official trial-0 slice of 54/97 (55.67%); official
  per-trial sums never fall below 51. Its post-run validation initially
  failed only because an evaluation-only commit landed mid-run (a repeat to
  avoid: no commits while a guarded run executes); a `revalidatable` resume
  branch now allows an unchanged, infrastructure-clean checkpoint to be
  re-validated under current code.
- Failure analysis of the nine tasks that officially pass 4/4 but failed
  here: gold-action `call_discoverable_agent_tool` string mismatches are a
  red herring (the official run records the same `action_match: false` on its
  own passing trajectories; these tasks grade on DB only). The real failures
  are behavioral: the agent computed wrong values or made wrong choices
  (wrong credit amounts, wrong account classes) or omitted required calls
  (an unexecuted third credit in task_073 that the agent nevertheless
  reported to the user as applied; an unlocked-but-never-called tool in
  task_056; a merely-grepped freeze tool in task_079). A gold-DB replay diff
  confirmed the graders are exact. Agent completion/reasoning token
  distributions match the official run (mean 662/509 vs 677/513), ruling out
  provider-side reasoning degradation.
- Interpretation: the drop concentrates on knowledge-computation tasks that
  the ten-task gate never exercised, consistent with the accepted
  OpenRouter-constrained non-parity (dense retrieval content differences and
  the missing user-simulator tool harness) plus single-trial sampling
  variance; a single sample cannot separate the two. A second single-trial
  run (~$68) would discriminate: a repeat in the low 40s confirms a
  systematic environment gap, a return to ~52+ points to an unlucky draw.
- Nemotron resume validation additionally accepts a recorded
  reference-config digest that hashes the exact committed blob at the
  manifest's own runtime head under the modes.full-only proof, completing the
  evaluation-only delta handling for its receipts.

## 2026-08-22 — agent-owned full-trace audit and contract reconciliation

- Applied the merged `benchmark-parity` skill to the completed single-trial
  checkpoint instead of treating its summary as a reproduction. Retrieved the
  immutable Linux-host checkpoint and manifest into a temporary local audit
  directory; their SHA-256 digests match the source exactly:
  `6e50333ae5b13cac0048194ac6214ed7201e0a422dfb90a86d4c45dd6f06f3dc`
  and `9a4003933b1554ffd6cf340ba819b4f5876cb993168ed734ced941a5cadaf5d3`.
  No model, embedding, judge, or Modal call was made.
- Exact score audit confirms **41/97**, not parity with official trial 0's
  **54/97**. There are 23 task flips: five official failures became passes
  (`008,014,057,074,102`) and 18 official passes became failures
  (`033,034,040,043,044,051,054,055,056,059,070,071,073,078,079,089,093,094`).
  Offline authoritative DB/ACTION/NL recomputation reports zero grading-
  integrity issues, so the 13-point net gap is not a grader bug.
- Trace audit shows a real mixture of hosted sampling and transport/retrieval
  drift. For 39/97 tasks the first generated user message and the first Qwen
  prompt-token count are both exactly equal to official, yet **0/39** first
  Qwen outputs match despite the same Alibaba route, xhigh arguments, tools,
  and seed. Seven of the 18 official-pass-to-fail tasks are in this identical-
  first-input set. The other 11 begin with a different GPT-5.2 user response,
  consistent with the accepted OpenRouter-vs-direct-OpenAI user transport gap.
- Secondary metrics are close but not equal: candidate vs official generated
  participant messages `2,987` vs `2,909`, tool calls `3,756` vs `3,604`, mean
  duration `383.3251s` vs `393.5313s`, Qwen completion/reasoning tokens per
  generation `661.55/508.95` vs `677.34/512.53`, and serialized participant
  chat cost `$68.32762455` vs `$62.2505533`. Both traces use the same 20
  observed tool names; the declared initial tool schema remains 17 tools with
  SHA-256 `5e2d300ebc61227f1f79119768fe3c191a27896cbe844be7ccd49b0e9c271ae1`.
- Reconciled the local branch with the nine published fork commits and removed
  the duplicate `full_trial0` mode. `full` is the single canonical 97-task,
  trial-zero mode. Its frozen historical credit requirement now uses the exact
  official trial-zero serialized chat cost `$62.2505533`, rather than one
  quarter of the four-trial aggregate. Added the skill's `benchmark.toml` and
  corrected README commands/counts.
- Fixed comparison provenance for an unchanged completed checkpoint that is
  revalidated by a later evaluation-only commit: the manifest may bind the
  revalidation HEAD only after `evaluation_only_commit_delta` proves every
  intervening path is in the guarded allowlist. This keeps the original scoring
  commit in the result while allowing the bound endpoint inventory to be
  trusted for route validation; non-evaluation code drift remains fatal.
- Re-ran the complete offline comparator in place on the Linux evaluation
  host after publication. Report SHA-256
  `c59a54a7406c15e80971210c734c457a4672e6a4e5d3f633cd95be8b60c9eb83`
  proves configuration, structure, execution-manifest, raw participant routes,
  task-102 judge route, and grading integrity all pass with zero issues. The
  failure is explicit: reward `41/97` vs `54/97`, 23 task-vector flips, 64
  component differences, 6,195 tool-behavior differences, and 1,196 generated
  participant text differences. Strict and aggregate parity are both false.

## 2026-08-22 - guarded Qwen 3.8 Max trial-0 repeat and parity report

- Published clean evaluation commit
  `e28b25b8719e743a7ec7f36bb6dbf3a0b5d59bad`, repaired the existing exact
  22/40 aggregate subset gate by revalidating its immutable candidate under
  the evaluation-only ancestry guard, and verified the full dry plan. The
  authoritative OpenRouter credit preflight recorded `$825.9298108689982`
  remaining against the frozen `$62.2505533` official trial-0 participant-chat
  cost. The key was never logged, copied, or serialized.
- Launched exactly:

  ```bash
  ALLOW_FULL_RUN=1 uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/run.py full \
    --output-dir reproduction/tau3_banking/runs/qwen38_full_trial0_repeat \
    --execute --confirm-paid-api-calls --cost-ceiling-usd 150 \
    --allow-known-full-shell-drift
  ```

  The run started `2026-08-23T00:58:35Z`, completed
  `2026-08-23T02:16:10Z`, and exited 0. Post-run validation proves 97/97 exact
  task/trial keys, seed `626729`, 97 `user_stop`, zero infrastructure errors,
  valid protocol and response IDs, zero grading-integrity issues, exact
  Alibaba Qwen routes for 2,249 responses, exact OpenAI/default GPT-5.2 routes
  for 652 responses, and the dated OpenAI GPT-4.1 task-102 judge route. Result
  SHA-256 is
  `92051d8923946012e609ad1f25cbc6f57754f8a49746e28fc8b9babb3a93e2d3`;
  manifest SHA-256 is
  `ea174dcb8464014752ec3f0cbc88415eb0a3de2d1ace7bc6267c565deb2731ce`.
- **Result is NOT EXACT:** reproduced **43/97 (44.329896907216494%)**
  versus official trial 0's **54/97 (55.6701030927835%)**, a delta of -11
  passes / -11.340206185567012 percentage points. Twenty-three tasks flipped:
  official pass to reproduced failure
  `005,016,033,040,045,048,049,051,054,059,070,071,072,078,094,096,101`;
  official failure to reproduced pass `007,008,014,057,090,099`.
- Strict comparator SHA-256
  `fce8b34d20aff5745315910623185d453aae68837bd9f7c0e16a6c50e8d9accb`
  reports 69 component differences, 6,424 behavior differences, 1,183
  participant-message differences, 1,186 tool-call differences, and 5,238
  tool-output differences. Configuration, structure, execution manifest, raw
  routes, judge route, grading integrity, and sampling attribution each have
  zero issues. All 6,424 behavior differences are causally attributable to
  model-selected sampling drift, but aggregate parity is false and therefore
  cannot be waived.
- Trace boundary audit strengthens the hosted-nondeterminism finding. Forty-
  seven tasks have byte-identical first generated user text and the same first
  Qwen prompt-token count as official, yet **0/47** first Qwen outputs match.
  Across the first GPT-5.2 calls, candidate prompt tokens are exactly 81 lower
  on 81 tasks and equal on 16, consistent with the known OpenRouter-vs-direct-
  OpenAI user transport boundary. Provider tokenizer revision, Jinja chat
  template, and BOS/EOS policy remain unobservable; current-call Qwen thinking
  is preserved in raw trace and stripped from subsequent history by the same
  tau2 renderer.
- Secondary metrics, candidate vs official: generated participant messages
  `2,901` vs `2,909`; tool calls `3,840` vs `3,604`; observed tool names `18`
  vs `20`; mean duration `428.2069s` vs `393.5313s`; participant chat cost
  `$73.70333065` vs `$62.2505533`; Qwen completion/reasoning tokens per
  generation `734.2939/578.6910` vs `677.3438/512.5318`. The task-102 judge
  added `$0.10739`; embeddings, Modal, and discarded retry spend are excluded.
- One live whole-simulation restart occurred on task 054 after Qwen returned
  an empty final `AssistantMessage` with neither content nor tool calls. The
  pinned upstream harness retried it and retained only the eventual
  `user_stop` attempt. This is disclosed as process non-parity: the parity
  contract permits only typed infrastructure retries, and the discarded
  attempt's spend is not recoverable from the final checkpoint.
- Added a deterministic offline analyzer and compact receipt. Metrics receipt
  SHA-256 is
  `6ba4b73045ff47414295e5f4b0cbeafc9efbc0d0ab32d5ad69f379ed09e87561`.
  Generated and visually inspected all four pages of the linked parity PDF;
  its renderer verified extractable text and all 16 external URI annotations.
  PDF SHA-256 is
  `17d6e27ee7c69a43a772a8946aa4315df0f0d0d8b6671d3410486f8b5a65f2be`;
  PDF QA receipt SHA-256 is
  `efa1d54729fdb44dcb3c0550648979cc060bff9bcbbb9f6a7755111d4fddb716`.

## 2026-08-22 - direct-OpenAI readiness check

- Two complete Qwen trial-0 evaluations now independently score `41/97` and
  `43/97` against the official `54/97`, with clean deterministic grading and
  provider-route validation. This is evidence of a systematic parity gap; a
  third unchanged full run would not be an evidence-backed correction.
- A read-only host check found `OPENAI_API_KEY` present on the Linux evaluation
  host. Authenticated model-metadata requests resolved `gpt-5.2`,
  `gpt-4.1-2025-04-14`, and `text-embedding-3-large`. No key value, key hash,
  account label, project identifier, response header, or raw credential-bearing
  request was logged or copied.
- The first isolated direct-OpenAI operation attempted to build the 698-document
  `text-embedding-3-large` cache outside the scored checkout cache. OpenAI
  rejected it before computation with HTTP 429, error type
  `billing_not_active`; zero embeddings were returned and no cache was written.
  This happened before any Qwen, GPT-5.2 user-simulator, GPT-4.1 judge, or Modal
  call in a new evaluation. The redacted receipt for the latest one-input
  readiness probe is `reports/direct_openai_readiness.json`, SHA-256
  `e5278decd94811f4633b7827b458e974a55e7186a2d3640e60888dfccb94f38f`.
- The next cost gate is therefore explicit: billing must become active for the
  existing credential; then rebuild and fingerprint the complete direct-OpenAI
  cache and compare official dense-query rankings before spending on one smoke
  or another 97-task x1 run. The original official cache and provider-managed
  Qwen tokenizer/Jinja revision remain unavailable, so even that path can prove
  aggregate-score parity but cannot promise byte-identical trajectories.
- Re-rendered and visually inspected all four report pages after this
  correction. Updated PDF SHA-256 is
  `294cc06f807ebac37faeb0865b5e041c5041c51b08599a396083caabbac32035`;
  updated link/text/page QA receipt SHA-256 is
  `95013e6ef9cb05bc02ac1bfee695e6367ff7b8d4508d59a0487f84c922fa034a`.
- Added `check_direct_openai.py`, a fail-closed readiness command that checks
  the exact three model IDs and optionally sends one small embedding input. It
  retains only status, error type/code, and returned dimensionality; it never
  stores the key, raw response, provider message, or embedding values. A second
  one-input check at `2026-08-23T02:58:39.231719+00:00` still returned
  `billing_not_active`; the ignored host receipt and committed redacted receipt
  have the same SHA-256 above. No full cache, Qwen, user-simulator, judge, or
  Modal call followed.

## 2026-08-22 - exploratory GLM-5.2 trial-zero run

- Added the thin guarded profile `run_glm52.py` and its tests in clean commit
  `8904806db686ba32420eeac80ced6a9fcc415f7f`, then pushed that commit only to
  `signalrush/tau2-bench`. The profile keeps the banking task set, GPT-5.2 user
  simulator, dated GPT-4.1 task-102 judge, `alltools` retrieval, Modal backend,
  seed `626729`, and concurrency 10. It changes only the participant to
  `openrouter/z-ai/glm-5.2`, pins `Sail Research` with fallbacks disabled and
  required-parameter enforcement, and requests temperature 1.0, top-p 1.0,
  16,384 output tokens, and `xhigh` reasoning.
- Launched the smoke exactly as:

  ```bash
  uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/run_glm52.py smoke \
    --output-dir \
    reproduction/tau3_banking/runs/glm52_smoke_8904806_20260823T0415Z \
    --execute --confirm-paid-api-calls
  ```

  Task 001 completed `user_stop` and scored 1/1. All route, response-ID,
  grading, provenance, and cost guards passed: 11 GLM responses used
  `z-ai/glm-5.2` through `Sail Research`, while three user-simulator responses
  used `openai/gpt-5.2` through OpenAI/default. Serialized participant cost was
  `$0.07850293` (`$0.07083268` participant and `$0.00767025` user). Results,
  manifest, and report SHA-256 values are respectively
  `af443c4c689be0eaf392a18300084d147572cc58821982e9646c72d0310c9672`,
  `59f03a0c2914ef8aa2e70e7150747fb5893d4b94f317a1fb7c05f44049fe4ba5`,
  and `b26d0b5f7f6ee338df48351fb31e64888bb47506cf1eb606bca2bad032352688`.
- Launched the 97-task x1 run exactly as:

  ```bash
  uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/run_glm52.py full \
    --output-dir \
    reproduction/tau3_banking/runs/glm52_full_8904806_20260823T0420Z \
    --smoke-manifest \
    reproduction/tau3_banking/runs/glm52_smoke_8904806_20260823T0415Z/glm52_manifest.json \
    --execute --confirm-paid-api-calls
  ```

  The guarded account-wide preflight at `2026-08-23T04:09:42Z` recorded
  `$34,010.00` total credits, `$33,742.190922779` total usage, and
  `$267.809077220998` remaining against the mode's `$100` admission gate.
  This is an admission check, not an account reservation or hard spend cap.
- The run later received OpenRouter HTTP 402 errors with
  `limit_source=openrouter_credits`. It was interrupted by signalling only its
  resolved remote process group after the failures became persistent; the
  wrapper finalized `failed` with exit code 130 at
  `2026-08-23T04:29:12.580051Z`. No evaluation worker remained afterward.
  The resumable checkpoint contains 95/97 task records: 24 valid `user_stop`
  trajectories, 71 infrastructure-error placeholders, and two tasks not yet
  started. The 24 valid records provisionally sum to 15 rewards, but **15/24
  is not a full-set score and must not be reported as GLM-5.2 performance**.
  Their serialized costs total `$2.10844035` for GLM and `$0.39937310` for the
  user simulator; discarded provider retries and infrastructure failures are
  not represented by those checkpoint totals. The account-level credit loss
  therefore cannot be attributed to this run from serialized trajectory cost.
- The stopped checkpoint and failed manifest SHA-256 values are respectively
  `5128e2dbf895bc00aa877a30933349469199d53d286cba99fbe97e5c6e8afa76`
  and `97c6be3d2ebba8c81be6f6db05a31a0783aafd9d35f5a50e44087bc336b7698c`.
  A future continuation must use the same clean commit, smoke manifest, output
  directory, and command with `--resume`; upstream checkpoint semantics will
  preserve the 24 validated trajectories and retry only infrastructure-error
  and missing task keys. It must not start until the guarded credit preflight
  again covers the selected mode.
## 2026-08-22 — trace analysis: the deficit is systematic, and its mechanism

Two independent guarded single-trial runs (both `completed`, exit 0, same
committed runtime, agent `openrouter/qwen/qwen3.8-max` effort `xhigh`, seed
300):

| run | score | cost |
|---|---|---|
| `full1t_c3887fe` | **41/97 = 42.27%** | $68.33 |
| `qwen38_full_trial0_repeat` | **43/97 = 44.33%** | $73.70 |
| official trial 0 | 54/97 = 55.67% | — |

Official per-trial sums are `[54, 56, 51, 53]`. Under the official per-task
rates the single-trial distribution has E=53.50, sd=2.69, so our two runs sit
at z = −4.64 and −3.90; `P(single ≤ 43) = 9e-5` and `P(both ≤ 43) ≈ 1e-8`.
**The gap is systematic, not sampling.** Run-to-run behaviour is otherwise
normal: our A-vs-B per-task agreement is 75/97 (77.3%), essentially the same
as official's own trial0-vs-trial1 agreement of 79/97 (81.4%).

### The harness is not the cause

Checked against the official artifact directly:

- Agent system prompt/policy byte-identical for all 97 tasks (SHA-256
  `a097943f9b9d8823…`); `agent_info` and `llm_args` identical.
- Shell is healthier than the historical backend: 0.2% failing commands vs
  official's 0.5%; fewer shell errors per task.
- Retrieval yield identical: 9.5 documents per search call in both; our runs
  see slightly *more* unique documents per task (49.1/50.5 vs 47.4).
- User simulator comparable: 7.3/6.7 vs 7.0 user messages per task, ~305
  characters and ~90 completion tokens in both.
- Agent completion/reasoning token distributions match (mean 662/509 vs
  677/513), ruling out provider-side reasoning degradation.
- All 97 simulations `user_stop`, zero infrastructure errors, exact
  Alibaba/OpenAI routes.

### The cause: dense-retrieval drift against deliberately planted distractors

The only remaining non-parity in the scored path is the embedding transport:
the official run embedded through direct OpenAI, this reproduction must use
OpenRouter. The measured drift is that only 65.8% of dense calls return the
exact official top-10 ordering (1,188/1,806), even though aggregate score
distributions are nearly identical (mean 0.5187 official vs 0.5179 ours).

That modest ranking drift is score-decisive because `banking_knowledge` is
engineered around near-duplicate documents whose selection flips the answer:

- **task_070** (official passes 4/4; both our runs fail identically).
  `doc_bank_accounts_bank_accounts_(general)_013` is ACTIVE 11/01–11/30 and
  directs "recommend Sky Blue first"; `…_014` is EXPIRED 10/12–11/12 and
  directs "recommend Lime Green, then Hunter Green". The simulated date is
  2025-11-14. **Official retrieval surfaced `_013` four times and never
  surfaced `_014` at all**; both our runs surfaced `_014` three times each.
  Both our runs answered `account_class="Hunter Green"`; gold and official
  answer `"Sky Blue"`.
- **task_059** (official passes 4/4). `…_001` documents the convention
  `'Green Account (checking)'` while `…_002` documents `'Silver Plus
  Account', 'Gold Account'`. Both our runs wrote
  `account_class="Green Account (savings)"`; gold is `"Green Account"`.

The failure signature matches this mechanism rather than execution failure.
Among DB-graded failures, "spurious write" (correct action, wrong argument)
appears in 22.6% of ours versus 7.5% of official's; 16 of our 18 trial-0
regressions are DB failures, and the concrete diffs are wrong product classes
(`Purple`/`Gold` for `Silver Plus`, `Hunter Green` for `Sky Blue`), wrong
knowledge-derived amounts (131.43 and 143.48 for gold 140.00), and wrong
account IDs — not missing execution ability.

Decisively, **4 of the 9 tasks that official passed and both our runs failed
produce byte-identical wrong mutating-call sequences across two independent
samples**. Independent sampling cannot produce identical wrong answers; a
shared environment difference can.

### Conclusion

The reproduction does not reach the official number, and cannot while the
OpenAI-embedding transport is out of scope. The harness reproduces the
official configuration exactly; what it cannot reproduce is the official
`text-embedding-3-large` document cache, and this benchmark's score is
unusually sensitive to that cache because its corpus is built from
conflicting near-duplicate documents. Expected reachable range on the current
transport is ~42–44/97 (43.3% pooled) against an official 55.7%.

Closing this out requires a billing-active direct-OpenAI key to rebuild the
document cache on the official transport; that is the single remaining
variable, and the harness already contains the direct-OpenAI code path
(reverted to OpenRouter per owner direction, recoverable from commit
`3930fbb`).

### Spend

OpenRouter credit is exhausted (−$8.00 at the time of writing). All paid
processes were stopped. Recorded run costs this session: two full trial-0
runs $68.33 + $73.70, the 40-run subset gate $10.77, the earlier subset
$11.93, plus interrupted/partial runs. An interrupted four-trial full run
(`full_6c4aa41`) was cancelled after the owner reduced scope to one trial;
its in-flight simulations were paid for but not serialized.

## 2026-08-22 — CORRECTION: embeddings were never the cause

An owner-supplied direct-OpenAI key made the decisive experiment possible.
The previous entry attributed the 41–43/97 deficit to OpenRouter-vs-OpenAI
dense-embedding drift. **That conclusion was wrong** and is retracted here.

### The two caches are numerically equivalent

Built the 698-document cache on the official transport (direct OpenAI,
`text-embedding-3-large`, ~$0.13) and compared it row-by-row against the
OpenRouter cache that both full runs actually used, aligned by document ID:

- mean cosine `0.99997339`, median `1.00000000`, min `0.99736280`
- documents below cosine 0.9999: 33/698; below 0.99: **0/698**

OpenRouter genuinely proxies to OpenAI; the vectors are the same to within
float noise.

### Retrieval parity does not improve

Head-to-head on the 444 official trial-0 dense queries, with query embeddings
held constant so only the document cache varies:

| document cache | exact top-k order | top-1 | doc overlap |
|---|---|---|---|
| OpenRouter (used by both runs) | 296/444 (66.7%) | 99.3% | 99.03% |
| direct OpenAI (official transport) | 308/444 (69.4%) | 99.1% | 99.01% |

Switching to the official transport moves exact ordering by +2.7 points while
top-1 and set overlap move −0.23 and −0.02 points. That is noise, not a fix.
The residual ~30% ordering difference is tie-breaking between near-identical
scores (mean |Δscore| on top-1 is `0.00029`), not a content difference: the
retrieved document *set* is ~99% identical either way.

Note also that the cache-loading path is correct: `EmbeddingsCache.get`
remaps rows by document ID, so the OpenRouter cache's macOS-order storage was
never mis-mapped to documents.

### Independent evidence that retrieval is not the mechanism

- The deficit is **largest on the tasks needing the least retrieval**:
  −23.5 points on low-retrieval tasks (≤10 search calls), −12.0 mid, −10.0
  high. A retrieval defect would show the opposite gradient.
- On our wrong decisive arguments (account class, card type, amount), the
  gold value was present in the agent's own retrieved context **12/12 times**.
  Nothing needed was missing.
- Competing product names visible in context are no denser in our runs than
  official's (−0.7 and −0.3 on average).

### What the evidence now says

Everything testable is faithful: agent policy byte-identical on all 97 tasks,
identical model/args/routes, 581/595 identical outputs for identical
non-retrieval tool calls (the 14 differences are all path-dependent state),
shell healthier than the historical backend, comparable user simulator, and —
on 39 tasks where the agent's input is byte-identical (prompt_tokens equal
4568.0 in 39/39) — the same first-tool distribution
(`KB_search_dense` 24 vs 23, `KB_search_bm25` 13 vs 14), so no measurable
model drift.

The deficit has a precise shape instead:

| official 4-trial rate | n | expected | run A | run B |
|---|---|---|---|---|
| 4/4 | 34 | 34.0 | 25 | 27 |
| 3/4 | 18 | 13.5 | 9 | 9 |
| 2/4 | 5 | 2.5 | 2 | 3 |
| 1/4 | 14 | 3.5 | 4 | 4 |
| 0/4 | 26 | 0.0 | 1 | 0 |

We match official *exactly* on every task it finds hard, and lose ~25% of the
tasks it solves reliably. Our two runs fail largely disjoint subsets of those
(9 and 7, overlap 3, versus 2.0 expected under independence), so it is a
random per-simulation fault, not a deterministic one. Failing simulations also
run far longer than passing ones (434s and 557s vs 237s and 260s; official
averages 264s on the same tasks).

That signature — reliable tasks failing intermittently, long unproductive
trajectories, no missing information, no config or model difference — is the
open question. It is not retrieval, not embeddings, not grading, and not the
sandbox.

## 2026-08-23 - completed GLM-5.2 trial-zero run

- Replaced only the authoritative OpenRouter credential in
  `~/.rllm/config.json` on the evaluation host. The key was entered with
  terminal echo disabled, written atomically with mode `0600`, and was never
  printed or copied into a command, artifact, or log. The first guarded check
  for the new account at `2026-08-23T04:39:05.865680+00:00` recorded
  `$4,100.00` total credit, `$3,135.067771202` usage, and
  `$964.9322287979999` remaining against the full mode's `$100` gate.
- Continued the existing checkpoint with this exact authenticated command:

  ```bash
  uv run --frozen --extra knowledge python \
    reproduction/tau3_banking/run_glm52.py full \
    --output-dir \
    reproduction/tau3_banking/runs/glm52_full_8904806_20260823T0420Z \
    --smoke-manifest \
    reproduction/tau3_banking/runs/glm52_smoke_8904806_20260823T0415Z/glm52_manifest.json \
    --resume --execute --confirm-paid-api-calls
  ```

  The same command was used for every cleanup launch. Upstream auto-resume
  skipped every validated task and retried only infrastructure placeholders;
  no output was replayed, copied, or cherry-picked. The four guarded launch
  receipts form the checkpoint chain
  `null -> 5128e2db... -> 09f4c0a9... -> 03a69db5... -> 84c89c9a...`.
- The paid continuation first reached 92 valid trajectories and five
  placeholders (`task_073`, `task_074`, `task_082`, `task_090`, and
  `task_091`). The next cleanup reached 95 valid with only `task_074` and
  `task_082` remaining. The final cleanup reached 97/97. Across these
  post-credit launches, 36 attempts were discarded for a provider response
  with an empty terminal assistant message and nine for transient TLS
  `SSLV3_ALERT_BAD_RECORD_MAC`; discarded attempt spend is not serialized in
  `results.json`. No 429, 402, route fallback, grading error, or Modal failure
  occurred after the new account was installed. The earlier interrupted
  checkpoint's 71 HTTP-402 placeholders and two missing tasks remain recorded
  separately above.
- A later commit (`74a3907`) changed committed embedding-cache metadata after
  this evaluation had started. The smoke/runtime guard correctly rejected one
  cleanup attempt before its credit, model, embedding, or Modal calls. Cleanup
  therefore ran from clean commit
  `4643dc52d58538e5e897b761d6e061f2edc88a49`, the exact prior evaluation
  runtime accepted by the original `8904806` smoke receipt. The checkout was
  restored to the published branch afterward. No guard was weakened and no
  cache or result was transplanted.
- Final validation passed with exactly **97/97** completed trajectories, zero
  infrastructure errors, and 97 `user_stop` terminations. The score is
  **33/97 = 34.02061855670103%**. Participant routing is exact: 2,450
  assistant responses used `z-ai/glm-5.2` through `Sail Research`, and 708
  user-simulator responses used `openai/gpt-5.2` through OpenAI/default.
  `task_102` used the required dated judge
  `openrouter/openai/gpt-4.1-2025-04-14`, resolved to OpenAI, and its NL
  assertion passed; its overall trajectory reward remained zero because the
  DB check failed.
- Retained serialized costs are `$21.61216452` for GLM-5.2,
  `$1.93359775` for GPT-5.2 user simulation, and `$0.11268` for the dated
  GPT-4.1 judge: **`$23.658442270000002` total**. This excludes embeddings,
  Modal, and discarded attempts. The free post-run account check at
  `2026-08-23T08:08:07.358831+00:00` recorded `$3,165.241331872` usage and
  `$934.758668128` remaining against the Nemotron mode's `$40` gate. Account
  usage is account-wide and is not used as an attributed run-cost total.
- Final SHA-256 receipts:

  - `results.json`:
    `84c89c9a0a87a5aaf0c6a16998e4333a860ae3d810c815690cf6619c96667774`
  - `glm52_manifest.json`:
    `639cc89544a4aa72bf7c16c89770825cb406ed00f6f7e16e7effbaa6ee0ea942`
  - `glm52_report.json`:
    `f5c21ac6869c2be2c20c78e68f1e6695cee321e8a1ab346833198284c4a3caed`
  - validated coverage:
    `b503c87e6d607ae4c8abc98a98ac2dc09bf3862a0640e9ed353b12ae922f43d2`
  - participant response IDs:
    `635b9a31cf9088fabc4294c40a3ce2886aeba66fc88682a1e3032aa8bf595b1f`
  - judge response IDs:
    `26411e877388b8cbb76007f210c2b7ef4207467be73f92b067835dbde4688fff`
