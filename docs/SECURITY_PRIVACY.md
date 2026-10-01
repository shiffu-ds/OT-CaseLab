# Security, privacy and reliability design

Prototype v0.1 — 1 October 2026. This records controls and release limits; executed abuse outcomes are in [IMPLEMENTATION_STATE.md](IMPLEMENTATION_STATE.md). It does not certify regulatory compliance or completion of an independent security audit.

## Trust and ownership

Browser sessions use random opaque tokens, hashed in the database, HttpOnly/SameSite cookies, expiry and logout deletion. Production configuration requires HTTPS origin, secure cookies and PostgreSQL. Credentials use Argon2. Unsafe authenticated requests require a session-bound CSRF header; Origin is checked separately, including login/registration. Public registration creates students only and is disabled when demo allowance is false; institutional invitations remain backlog. Login failure counters are persisted using hashed account/IP keys.

Database object policies bind attempts, assets, jobs, feedback and reports to the learner or authorized same-cohort educator. Public serializers explicitly allowlist learner fields; hidden facts/rubric are server-side. Internal MCP has transport bearer authentication and a separate signed scope. Every tool rechecks live user, cohort, attempt and permissions; the model cannot choose identity. App database role `otcase_app` has no superuser, create-database or create-role privileges. Database owner credentials are kept for controlled backup/administration.

## Input and model controls

Text/file lengths, job inputs and identifiers are bounded. Uploaded raster images are validated and re-encoded with metadata removed; private paths never originate from model output. Original supplied assets use a fixed identifier/path allowlist. No arbitrary external URL fetch is needed. Document/learner text is data, not instructions. Case/dialogue selection schemas reject undeclared provider output and invented facts. MCP scopes, deadlines, call budgets and case eligibility remain deterministic. Numeric JSON recommendation artifacts are validated; no untrusted pickle is loaded. Provider secrets remain server-side and error text is redacted.

Feedback is provisional. Exact learner support, uncertainty, model mode and educator amendment history must be retained. No generated output is expert ground truth. Unsupported clinical conclusions and unavailable citations abstain. CV object output cannot establish measured clearance, accessibility compliance, diagnosis or treatment suitability.

## Data handling

Fictional demos contain no real patient records. The learning transcript belongs to the account and may contain identifying text that the user types; the interface should discourage real patient information. Research consent is optional for learning. Research exports default disabled and require authorized scope, current consent, de-identification and human free-text review. A pseudonymous export is not proven anonymous. Institutional consent/retention/legal review remains outstanding before real recruitment or cohort deployment.

Deletion removes eligible learner-owned attempts/messages/submissions/jobs/feedback/recommendations/session data and associated private uploads according to implemented ownership rules. Operational audit records should retain minimal metadata only. Backup expiration and any already-anonymized study aggregates require an agreed policy. A proposed operational starting schedule is 30 days for rotating encrypted backups with a monthly restore rehearsal, subject to the institution's decision; **no retention scheduler or off-host backup service is configured yet**.

## Required verification and residual work

Focused scenarios: wrong user/cohort access, forged/expired MCP scope, missing CSRF/foreign Origin, role injection, path traversal/invalid upload, hidden case keys, repeated writes/changed idempotency payload, malicious source instructions, provider outages, restart recovery and consent/deletion. Local tests cover only their fixtures and environment. Public HTTPS, independent penetration/a11y review, monitoring/alerts, total provider-spend enforcement, production retention and institutional identity/invitation controls still need release work where not shown by actual reports.

Log status, trace ID, action, duration and model mode; avoid dialogue, keys, session tokens and raw provider errors. Protect `.env*`, private runtime, backups and review exports with filesystem access. Production exposes Caddy ports only; MCP/DB/Redis stay internal. See [runbook](RUNBOOK.md).
