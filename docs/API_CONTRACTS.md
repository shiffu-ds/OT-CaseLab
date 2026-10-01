# API contracts and browser integration

Contract version 0.1, 1 October 2026. FastAPI's generated `/openapi.json` is authoritative for exact schemas. In development, interactive `/docs` is available on the API port. Browser code uses the same-origin `/api/v1` prefix; credentials and provider keys remain server-side.

All protected reads use the opaque session cookie. Protected writes additionally require `X-CSRF-Token` from login/`auth/me`. The frontend sends credentials and a JSON body; browser Origin must equal `APP_ORIGIN`. Login/register require Origin even before a session. Typical errors: 401 sign-in/expiry; 403 role/CSRF/origin; 404 unavailable or unauthorized object; 409 conflicting state/version/idempotency; 413 size; 422 invalid schema; 429 throttle; 503 unavailable provider. Hidden records use indistinguishable unavailable responses.

## Endpoints

| Method / path | Contract / permission |
|---|---|
| `GET /api/v1/health`, `/api/v1/ready` | Operational status/readiness, not model-quality certification |
| `POST /api/v1/auth/register` | `email`, `password` 12–200 chars, `name`, `language`; student only; demo allowance required |
| `POST /api/v1/auth/login` | `email`, `password`; sets HttpOnly cookie; returns user + CSRF + mode |
| `GET/PATCH /api/v1/auth/me` | Own session/preferences; `language` one of `en`, `ur`, `roman` |
| `POST /api/v1/auth/logout` | Revoke own session, CSRF required |
| `GET /api/v1/cases`, `GET /api/v1/cases/{case_id}` | Available scoped public case fields; no facts/rubric/hidden reference payload |
| `GET /api/v1/assets/{asset_id}` | Scoped supplied allowlisted asset; no arbitrary URL/path |
| `GET /api/v1/evidence?case_id=…&q=…` | Only approved passages in authorized case; explicit empty corpus allowed |
| `POST /api/v1/attempts` | `case_id`, `language`; binds immutable case/rubric version |
| `GET /api/v1/attempts?limit=50&offset=0` | Own paginated attempts; bounded pagination |
| `GET /api/v1/attempts/{id}` | Owner or authorized cohort educator; transcript/draft/status/report |
| `PATCH /api/v1/attempts/{id}/draft` | Owner, active attempt; bounded profile/observations/goals/rationale/evidence IDs |
| `POST /api/v1/attempts/{id}/messages` | Owner, active; `text` 1–3000 chars; scripted or configured patient reply |
| `POST /api/v1/attempts/{id}/messages/stream` | Server-sent completed event after validated generation; not provider token streaming |
| `POST /api/v1/attempts/{id}/submit` | Owner; bounded plan, prior interview, approved evidence IDs, `Idempotency-Key` required |
| `GET /api/v1/attempts/{id}/feedback` | Scoped provisional report plus preserved educator amendments |
| `GET /api/v1/attempts/{id}/report` | Scoped Markdown attachment with provenance/version/status |
| `POST /api/v1/attempts/{id}/analysis` | Owner, own observations required; assigned `asset_id`; durable job, status 202 |
| `GET /api/v1/jobs/{id}` | Scoped state/result/error, no another learner's job |
| `GET /api/v1/progress` | Own attempt history, provisional aggregate coverage and recommendation |
| `GET/POST /api/v1/educator/cases` | Same-cohort educator; create original validated draft payload |
| `POST /api/v1/educator/cases/{id}/versions` | Educator; new draft version, existing attempt version retained |
| `POST /api/v1/educator/cases/{id}/publish` | Educator; explicit review note ≥20 chars; reviews case/rubric and included passages |
| `GET /api/v1/educator/attempts` | Authorized cohort pagination |
| `POST /api/v1/educator/attempts/{id}/review` | Educator; reason ≥10 chars and optional original dimension scores 0–3 |
| `POST /api/v1/privacy/consent` | Own versioned opt-in/withdrawal `granted` boolean |
| `DELETE /api/v1/privacy/me` | Own eligible records/session/upload deletion; CSRF |

Example plan (fictional educational task):

```json
{
  "profile": "Ask which morning activity matters most and what help is preferred.",
  "observations": "The image shows a chair and shelf; clearances are unmeasured.",
  "goals": "Agree an observable dressing activity tied to the stated priority and a review criterion.",
  "rationale": "Confirm missing context and restrictions with an educator before choosing a plan.",
  "evidence_ids": []
}
```

The minimum length validates presence, not educational quality. A frozen submission checksum and stable idempotency key govern retries. A changed retry payload conflicts rather than creating a different grade. `active`, `evaluating`, `completed`, `failed` are persisted attempt states; failure is recoverable using the original payload/key. Image jobs separately expose queued/running/completed/failed state and deduplicate assigned input/model mode. No endpoint is a real-patient diagnostic/treatment API.
