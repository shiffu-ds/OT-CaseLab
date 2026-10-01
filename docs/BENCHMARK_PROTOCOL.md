# Predeclared benchmark and pilot protocol

Protocol draft v0.1, 1 October 2026. **No human study or educational effectiveness evaluation has occurred.** Educators and the relevant institutional review process must finalize this protocol before recruitment. Proposed targets below are gates to be agreed, not results.

## Questions and comparisons

H1: equivalent reasoning expressed in English, Urdu and Roman Urdu receives consistent provisional feedback. H2: interview plus image reasoning improves integration of priorities/context on a new task relative to a matched interview-only task. H3: exact learner excerpts, rubric anchors and approved passages improve educators' correction decisions and learners' explanation comprehension relative to otherwise matched feedback.

Compare educator-written static cases and a specified general-purpose AI baseline under the same case facts, time and permitted resources. Where commercial authoring/access is authorized, use the same case; otherwise match competencies and report interface/content differences. Do not rank platforms from unequal tasks or marketing claims.

## Design

The target audience is adult OT students in a course agreed with its educators. Inclusion, language proficiency, recruitment, incentive and exclusion details remain to be finalized. Participation must be voluntary and separated from high-stakes grades. Two independent educators score de-identified learner work; blind them to study arm where feasible. Pilot feasibility first, then determine a sample size using the smallest educationally useful effect, variance and clustering estimated with educators/statisticians; no arbitrary sample certifies validity.

Randomize/counterbalance equivalent tasks and account for repeated observations, case difficulty and baseline knowledge. Learning transfer uses a new case withheld from practice. Paraphrases and near-duplicate cases belong to the same family. Intervention arms must not receive answer-key hints unavailable to controls.

## Measures and frozen evaluation rules

| Component | Measures | Required holdout / interpretation |
|---|---|---|
| NLP | Span-level precision/recall/F1, field accuracy, negation and unknown errors by language and code-switching | Independent reviewed spans; fixture outputs are not ground truth |
| Feedback | Educator ordinal agreement, weighted kappa or ICC with assumptions, supported-claim proportion, correction and abstention rates | Frozen rubric and blinded double ratings; generated feedback cannot be sole evaluator |
| CV | Object AP/precision/recall, coordinate alignment, failure examples | Licensed staged representative photos, independent labels; contextual barrier interpretation measured separately |
| Retrieval | Recall@k, passage precision, source coverage | Frozen reviewed questions and approved exact passages, scoped before search |
| Recommendation | Macro-F1, class metrics/confusion matrix; calibration if displaying probabilities | Learner-group holdout plus new-case family holdout where data permits; only pre-cutoff history inputs |
| Generative patient | Fidelity, unknown-fact handling, contradictions, answer-key leakage, provider failure behavior | Versioned prompts, approved facts and independent fidelity ratings |
| Agent | Completion, unnecessary calls, unauthorized calls, recovery, latency and cost | Compare fixed workflow under the same tool access and budget |
| Learning / usability | Independent transfer-task scores, completion, qualitative usability, perceived burden | Confidence alone is secondary, not proof of learning |
| Operations | Wall-clock time, CPU/RSS, queue delay, token/session cost, bytes transferred | Device/network/provider/model/cold-cache settings recorded; no unmeasured low-bandwidth claim |

Predeclare practical thresholds with educators before unblinding. Proposed hard gates: zero cross-user data disclosure in the specified abuse suite; every scored claim has exact learner support or explicit abstention; no retrieved unapproved passage; unknown facts remain unknown. These are behavioral checks, not statistical evidence of educational effectiveness. Use confidence intervals appropriate to clustered/repeated data, describe missingness and attrition, and avoid repeated final-test tuning.

## Ablations

Run matched arms with: retrieval removed; learner image task present without CV hints; CV assistance versus original annotations; baseline recommendation versus candidate ML; fixed orchestration versus model-directed bounded agent. Isolate each change where feasible and avoid conflating multiple simultaneous interventions. Report unsuccessful hypotheses and additional cost as results.

## Data governance

Keep demo, pilot, training, validation and test data separate. Record consent/version/withdrawal, remove direct identifiers, review free text for identifying clues, restrict research exports and re-identification keys. A pseudonym is not full anonymization. Withdrawals stop future inclusion; handling already-anonymized aggregates must be stated in the consent approved by the institution. No real patient data is needed.

See [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md) for labelling and [RESEARCH_RESULTS_TEMPLATE.md](RESEARCH_RESULTS_TEMPLATE.md) for empty result fields.
