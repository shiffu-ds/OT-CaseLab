# OTCaseLab AI product brief

Decision date: 1 October 2026. This document scopes an educational prototype, not a completed efficacy study.

OTCaseLab lets an OT student interview a fictional adult, describe a supplied home/work image, assemble an occupational profile and functional goals, and inspect provisional feedback with exact learner excerpts. An educator can revise content and amend feedback. The proposed use is supervised formative practice in Pakistani educational settings, with English, Urdu script and Roman Urdu input. Curriculum fit must be agreed with the participating course; national alignment is unverified.

The primary objective is to justify a functional goal using a person's reported priority and relevant environmental context. A learner should ask about household preferences, support, resources and uncertainty. The five drafts vary people and occupations deliberately. No real patient records, mandatory camera, sensors or medical treatment workflow are needed.

The first complete journey is `stroke-home`. The other original drafts are `stroke-community`, `hand-work`, `desk-return` and `home-energy`. All content and annotations start `pending_review`; demo eligibility is separate from educator review and publication. Draft reference notes start unapproved. A scripted demonstration may therefore produce feedback without a reference citation and must state that limitation.

## Technology mapped to purpose

| Technology | Useful responsibility | Proof needed |
|---|---|---|
| Machine learning | Predict the next competency needing practice | Consented longitudinal data, independent educator labels, grouped held-out evaluation; rule baseline meanwhile |
| Deep learning / NLP | Pretrained language representation plus lexical mentions with exact offsets | Executed inference and reviewed multilingual span benchmark; pretrained use is not training |
| Computer vision | Object proposals for an image reasoning exercise | Actual neural inference, coordinates, licensed representative image benchmark; no barrier diagnosis |
| Generative AI | Case-constrained patient wording and bounded action selection | Configured provider, fidelity/error checks, versioned prompts and visible operating mode |
| Agent orchestration | Select permitted analysis/retrieval actions within a finite budget | Tool trace, deadlines, comparison with fixed workflow; deterministic baseline is labelled |
| MCP | Scoped internal access to case, analysis, evidence and progress tools | Real protocol initialization, discovery, calls, forged-token and isolation checks |
| Deployment | Same-origin web/API, persistent data, worker and internal MCP | Built stack, authorized hosting, HTTPS and restart/restore smoke evidence |

Success measures are complete journey rate, educator corrections, unsupported feedback rate, multilingual equivalence, transfer performance on unseen cases, usability, session cost, latency and transferred bytes. Their values are currently unmeasured. Learner confidence alone is insufficient evidence of improved reasoning. See [benchmark protocol](BENCHMARK_PROTOCOL.md).
