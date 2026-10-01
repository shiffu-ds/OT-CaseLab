# Model and baseline cards

Updated 1 October 2026. Reports record executed local mechanics and pretrained inference, **not educational validity**. Provider/configuration modes must remain visible in learner reports.

## Lexical NLP and rubric baseline

Implementation: `ai/baseline.py`, `ai/evaluate.py`. Original English/Urdu/Roman Urdu keyword/prototype rules preserve learner text offsets and local negation/uncertainty. Rubric coverage is provisional with exact submission/transcript support; it does not evaluate the full quality of OT reasoning. Interview evidence uses student messages, never patient replies. Unknown/missing content remains explicit.

Executed authored regression set: seven examples, unreviewed labels. `ml/reports/nlp-baseline-regression.json` reports F1 1.0 on its small English, Urdu and Roman Urdu fixture subsets. This only checks specified code paths; it provides no population accuracy or assessment-fairness estimate. No baseline training occurred.

## Pretrained multilingual neural candidate

Model: [paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, Apache-2.0 per model card checked 1 October 2026. Optional CPU SentenceTransformers path encodes clauses and compares them to original English prototypes; threshold 0.32, nearest-label output, exact original clause offsets. It is a reused pretrained encoder, not OT fine-tuning. Similarity is not a calibrated probability.

Actual report: `ml/reports/nlp-neural-smoke.json`. One English and one Urdu support clause were emitted; the Roman Urdu smoke input emitted **no entities**, a recorded failure/abstention example. Language fairness is unproven. Cold English run including weight download took 145,608.48 ms; subsequent Urdu/Roman runs 2,836.24 / 2,509.35 ms. Process maximum RSS reached 1,329,520 KiB. These are measurements from this run, not capacity guarantees or percentile latency; process high-water RSS is not isolated per-model memory.

Missing: independent educator-reviewed spans, spelling/code-switching coverage, precision/recall by language, calibration/task-specific adaptation. Fine-tuning is not implemented or claimed; insufficient approved data is the gate.

## Pretrained computer vision

Model: [Torchvision SSDLite320 MobileNetV3 Large](https://docs.pytorch.org/vision/0.23/models/generated/torchvision.models.detection.ssdlite320_mobilenet_v3_large.html), `COCO_V1`, Torch 2.8.0+cpu / Torchvision 0.23.0+cpu. Weights SHA-256 `a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2`. Optional neural mode rasterizes the original CC0 SVG and runs a genuine object detector; output is provisional pixel `xyxy` plus image dimensions. Baseline annotations and student observations are separate.

Actual report: `ml/reports/cv-smoke.json`, 1000×650 `room-home` raster, two chair predictions at confidence 0.89249 and 0.66055, threshold 0.5. One prediction overlaps the authored table area: useful failure evidence, not a confirmed observation. Elapsed 15,311.09 ms; maximum process RSS 407,180 KiB. Authored schematic versus photographic COCO domain mismatch is substantial. No AP, real-image accuracy, accessibility, fall-risk or clinical-suitability result is claimed.

Implementation licence: Torchvision BSD-3-Clause; demo image CC0-1.0. Preserve the linked weight/model provenance. A code licence and a training-data licence do not automatically establish every weight/dataset redistribution condition; record model-use permissions in any hosted release inventory.

## Scripted and optional generative patient

Default scripted mode selects relevant authored facts and renders their exact selected-language translations. Optional genuine Anthropic SDK adapter lets the configured model select at most two permitted utterance identifiers; validation rejects invented/undisclosed IDs and renders exact original text. This is constrained generation/selection, not open-ended patient paraphrasing or model training. Prompt version `patient-v1-constrained-selection` is preserved in provenance. Genuine provider credentials are unavailable, so no live Anthropic inference, price/cost or model-quality result is claimed.

Provider failures return a recoverable error without substituting a fake successful scripted reply. Model ID comes from configuration and should be verified against the authorized account before use. Official [tool schema documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) checked 1 October 2026.

## Next-practice recommender

Deployed mode: transparent lowest-covered-dimension rule restricted to eligible cases. Experimental training path: `ml/train.py`, scikit-learn logistic regression with median imputation, standardization and balanced classes, preprocessing fit on training only. Numeric JSON artifacts avoid loading untrusted pickle.

A real fit executed on **432 synthetic mechanics rows**, grouped split 324 train / 108 test, seed 71, no learner/case overlap. Report `ml/reports/synthetic-recommender/evaluation.json`: model macro-F1 0.7455; majority 0.0846; transparent rule 0.7370. These labels encode the fixture generator's prior-score rule. They do not estimate real student prediction, learning improvement or superiority; probabilities remain experimental. Promotion of synthetic artifacts to learner recommendation is denied. No consented longitudinal expert labels are available.

## Agent and MCP status

Default is `bounded_rule_workflow`, with an optional credentialed Anthropic planner that can choose an allowed analysis order and cannot change identities, arguments, writes or budgets. A deterministic workflow is not described as an executed model-directed agent. Genuine provider-planner execution remains pending credentials. Official MCP SDK 2.2.0 initialization/discovery/scoped actual calls and rejected scopes are exercised by `tests/test_mcp.py`; application bridge rechecks live database ownership. Component tests are software/security evidence, not educational quality evaluation. See [AI_PIPELINES.md](AI_PIPELINES.md).
