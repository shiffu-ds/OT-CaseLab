# Release plan and decision gates

Version 0.1 — 1 October 2026. An implemented module is not sufficient evidence that a release gate passed.

| Release | Required deliverable | Gate | Current evidence source |
|---|---|---|---|
| R1 one-case slice | Authenticated student completes stroke-home: interview, image observations, profile/goals/rationale, persisted provisional feedback, report; educator correction | Developer-free completion with fictional content; role/ownership checks; pending-review label preserved | API/UI/integration checks recorded in implementation state |
| R2 educational demo | Five cases, real neural NLP/CV invocation, provider adapter, approved evidence retrieval, bounded agent, real MCP, durable jobs and staging | Reviewed content and source permissions; actual model/provider traces; persistence and scopes; staging HTTPS smoke | Component reports plus deployment record; gate remains unmet while content/provider/staging checks are pending |
| R3 evaluated release | Expert-labelled recommendation; multilingual held-out benchmarks; ablations; authorized live audience | Consented data, independent educators, frozen holdouts, appropriate human-research review and measured uncertainty | Research results template remains empty until study/evaluations occur |

## Publication rules

Case review, demo eligibility and publication are separate states. Existing attempts bind to immutable case/rubric versions. A new draft needs a new version. An educator approval records attribution and a note; draft passages are only retrieved after their explicit approval. A release does not automatically approve content. Production should default `ALLOW_DEMO=false` and restrict access to its agreed cohort.

## Review gates

1. **Content gate:** educator reviews original case/rubric, translations and asset annotations; unresolved issues prevent reviewed publication.
2. **Feedback gate:** evaluated formative reliability is adequate for the intended use, or the system visibly defers uncertain items to human review. Targets must be agreed before analysis.
3. **Learning gate:** an appropriate pilot estimates transfer and incremental feature value with uncertainty. Confidence surveys alone do not satisfy this gate.
4. **Hosting gate:** authorized HTTPS environment passes login, full journey, configured inference, jobs, citation provenance, recommendation, MCP, educator correction, report ownership, service restart and restore checks.

No release gate is declared passed by this document. The implementation state and actual reports record executed outcomes.
