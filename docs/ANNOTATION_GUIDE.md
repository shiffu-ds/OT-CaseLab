# Annotation, consent and export guide

Draft v0.1 — 1 October 2026. No independent educator-labelled learner dataset is included. This codebook is a collection protocol requiring educator review.

## Content review

Review one immutable case version at a time. Confirm fictionality, educational scope, facts and unknowns; check all English/Urdu/Roman Urdu versions for equivalent meaning; verify household preferences are elicited rather than stereotyped; inspect image origin/licence and distinguish visible objects from interpretations. Confirm original rubrics are appropriate to the course. A demo-visible draft is not reviewed content. Inspect each included reference passage and its provenance/permissions before case publication; the current publish operation approves the included passages together. Granular passage approval is backlog. Preserve original text.

## Learner and language spans

Keep `text`, source message/submission ID and Unicode character offsets `[start,end)` exactly as submitted. `text[start:end]` must equal the annotation. Do not normalize spelling and then reuse original offsets. Annotate activity, priority, support, environment, symptom and goal, plus negated/uncertain flags. Record context when pronouns, sarcasm, code-switching or Roman Urdu spelling variation makes a label unclear. Unknown fields remain unknown. A patient-generated answer is not evidence of the learner's competency.

## Rubric ratings

Original dimensions: occupational interviewing; patient-prioritized functional goals; environmental reasoning; educational rationale. Each draft contains 0–3 formative anchors. Two educators independently rate the frozen learner content, identify exact supporting spans and record uncertainty. Adjudicate disagreements without overwriting first ratings; record reason and final consensus separately. Do not use LLM labels as expert truth or a proprietary scale without permissions. The deployed lexical coverage rule is a provisional software baseline, not an educator score.

## Image labels

Record original asset/checksum, dimensions, licence and review status. Demo authored boxes use normalized `xywh`; detector outputs use pixel `xyxy` with input width/height. Convert once for display and validate orientation after metadata removal. Mark visible object boxes/classes, occlusion and uncertainty. Do not label exact clearance, safety, posture, fall probability or clinical suitability without appropriate contextual measurements. A drawing's ground-truth labels do not make it representative of photographs. Keep student observations, authored annotations and CV proposals separate.

## Longitudinal recommendation rows

Target: the independently rated weakest competency in the next attempt. Inputs contain only history available before that attempt. Required identifiers: pseudonymous learner, case/family, row, prediction cutoff and target attempt. The implementation uses `profile` as the occupational-interviewing feature/target alias. Log prior scores/hints/missing dimensions and target provenance. Exclude future scores, language-style proxies and direct identifiers. All paraphrases and augmentations remain with their source case/learner.

Use connected learner/case groups for split manifests. If a learner appears in several cases, those rows must not straddle split groups. Fit imputers/scalers on training only. Freeze a held-out learner set and, where feasible, a separate unseen-case family set before tuning. Store dataset/split hashes and seeds. No final-test reuse for model selection.

## Consent and research exports

Institutional reviewers determine whether/how research review applies before recruitment. Learning participation and research consent must be separate. Describe purpose, data categories, access, risks, external providers, retention, withdrawal and already-anonymized aggregate handling in approved understandable language. Do not collect real patient information. The application defaults research exports disabled. Authorized educators export only permitted consented cohort records; identifiers are replaced and free text must be reviewed for identifying clues before distribution. An export hash/pseudonym alone is not anonymity.

Withdrawals stop new research inclusion. Track consent version/time and withdrawal before each export. Define a restricted re-identification map and delete according to agreed policy. Personal-data deletion, backups and aggregated research retention require a clear institution-approved schedule; the prototype does not establish legal compliance. Follow [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md).
