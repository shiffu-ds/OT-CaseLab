# Provider, retrieval, agent and MCP contracts

Implementation v0.1 — 1 October 2026. [MODEL_CARDS.md](MODEL_CARDS.md) records exact executed model reports and their limits.

## Operating modes and prompt registry

| Component | Default | Optional | Visible meaning |
|---|---|---|---|
| Patient | `PROVIDER_MODE=scripted` | `anthropic` with server-side credential/model ID | Authored scripted facts versus genuine constrained model selection |
| NLP | `NLP_MODE=baseline` | `neural` plus optional dependencies/weights | Lexical mentions versus pretrained prototype similarity, not validated OT extraction |
| CV | `CV_MODE=baseline` | `neural` plus weights/dependencies | Original draft annotations versus provisional neural object predictions |
| Recommendation | `rule_baseline` | Experimental numeric model pipeline offline | No synthetic-trained learner predictor deployed |
| Agent decisions | Rule | `AGENT_PLANNER=anthropic` | Optional model selection from permitted actions; no unrestricted autonomous actions |
| MCP transport | `stdio` local | `http` private service network | Real SDK transport in both modes; bearer and signed scope in HTTP mode |
| Jobs | `JOB_MODE=local` | `celery` plus Redis worker | Durable database records with local executor or hosted queue |

Prompt registry: `ai/providers.py` contains `PATIENT_PROMPT` (`patient-v1-constrained-selection`) and bounded planner instructions. Case/question/document content is untrusted data. The patient selects allowed IDs only; the renderer supplies exact authored translation. The planner receives bounded metadata/allowed actions rather than trusted identity. Neither can publish cases, approve evidence, change roles or supply a filesystem path.

## Retrieval and feedback

Case-scoped lexical retrieval checks educator approval before ranking. Passage IDs, exact text and origin are returned; no invented URLs are manufactured for original draft notes (`url:null`). Source text never executes instructions. At initial seed all evidence is unapproved: an empty result and missing-evidence uncertainty are valid, required behavior. Publishing after case review currently approves the reference passages included in that case together; granular passage approval is backlog.

Frozen learner submissions and student-message IDs supply score evidence. Patient dialogue is excluded as learner competence evidence. Feedback uses original rubric anchors, exact support offsets, case facts, relevant approved passages where available, provisional mode and uncertainty. Educator amendments append attribution/timestamps/reasons and retain original output. Lexical scores do not constitute educator agreement or clinical reasoning quality.

## Bounded workflow

Authentication, scope binding, immutable submission, idempotent save and object authorization are deterministic. The workflow loads context, performs permitted extraction/search, loads rubric, assesses the frozen learner content, recommends eligible next practice, and saves feedback through actual MCP. Limits: configured deadline and action budget (maximum eight calls by default); SDK errors and timeout produce explicit failure/abstention. Optional provider selection changes order within allowed actions; it cannot provide arguments or change writes. Tool traces preserve tool/status/elapsed time without printing private dialogue.

## Actual internal MCP tools

| Tool | Parameters beyond signed scope | Boundary |
|---|---|---|
| `get_case_context` | None | Context bound to authorized attempt/case version |
| `search_approved_evidence` | `query`, `k` 1–10 | Only approved case/cohort passages, bounded query |
| `extract_profile` | Bounded `text` | Learner span analysis, untrusted text |
| `analyze_case_asset` | `asset_id` | Assigned allowlisted asset, no arbitrary URL/path |
| `get_learner_history` | None | Server-bound learner history only |
| `get_evaluation_rubric` | None | Trusted internal evaluation scope |
| `assess_rubric` | None | Frozen database submission, not model-supplied answers |
| `save_feedback` | Validated `report`, `idempotency_key` | Signed write scope, allowed state, original retry semantics |
| `recommend_next_case` | None | Scoped history and eligible cases |

The real client initializes and discovers tools before calls. HTTP transport requires `MCP_HTTP_BEARER_TOKEN` of at least 32 random characters; a distinct `MCP_SERVICE_SECRET` signs short-lived attempt/learner/cohort permissions. A valid signature alone is insufficient: the bridge checks live rows and ownership. The server is not exposed through Caddy or public Compose ports. External-client authorization is not implemented or claimed.

Official SDK [v2.2.0 documentation](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/README.md) verified 1 October 2026. Normal REST routes are not described as MCP. Real component integration evidence is in the test run recorded by the implementation state; protocol mocks alone would be insufficient.
