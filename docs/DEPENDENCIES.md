# Dependency, licence and verification inventory

Verified 1 October 2026. `uv.lock` and `apps/web/package-lock.json` are the resolution authorities. Python runtime range is 3.12; installed development runtime 3.12.13, container Python 3.12.14. Verified host Node 24.19.0 and selected container Node 22.23.3 both meet the Next minimum; a completed container build is recorded separately from a version check.

## Locked major components

| Component | Selected / actual locked version | Purpose |
|---|---|---|
| FastAPI / SQLAlchemy / Alembic | 0.142.2 / 2.1.1 / 1.20.0 | Application, relational ownership and migrations |
| MCP / Anthropic SDK | 2.2.0 / 1.11.0 | Real protocol tools and optional genuine constrained provider |
| Celery / Redis Python | 5.6.3 / 8.1.0 | Durable hosted job transport |
| scikit-learn | 1.9.1 | Grouped experimental recommendation mechanics |
| Torch / Torchvision | 2.8.0+cpu / 0.23.0+cpu (optional) | Actual pretrained CPU inference |
| Transformers / SentenceTransformers | 4.57.1 / 5.1.1 (optional) | Multilingual neural candidate |
| Next / React | 16.3.8 / 19.3.0 | Browser interface |
| TypeScript / Playwright | 5.9.3 / 1.63.0 | Type and browser checks |
| uv | 0.10.8 | Locked Python installation |

This is a useful component list, not the entire transitive dependency set. [Recorded licence metadata](reports/dependency-licenses.json) includes 108 installed Python distributions and 64 locked npm entries in the initial inventory. Missing declared terms remain unknown. Regenerate using `.venv/bin/python infra/license_inventory.py` after a dependency change. Metadata inventory is not legal clearance or confirmation of model-weight/training-image rights.

## Production image selection

| Image tag | Primary verification source |
|---|---|
| `python:3.12.14-slim-bookworm` | [Docker official Python catalog](https://github.com/docker-library/official-images/blob/master/library/python) |
| `node:22.23.3-bookworm-slim` | [Docker official Node catalog](https://github.com/docker-library/official-images/blob/master/library/node) |
| `postgres:17.11-alpine3.24` | [Docker official PostgreSQL catalog](https://github.com/docker-library/official-images/blob/master/library/postgres) |
| `redis:7.4.11-alpine3.21` | [Docker official Redis catalog](https://github.com/docker-library/official-images/blob/master/library/redis) |
| `caddy:2.11.4-alpine` | [Docker official Caddy catalog](https://github.com/docker-library/official-images/blob/master/library/caddy) |

Exact tags were confirmed in the catalogs. Record actual pulled/built digests at release; a fixed tag alone is not an immutable binary. PostgreSQL17 is selected deliberately to use the stable volume path `/var/lib/postgresql/data` and avoid assuming another major version's storage layout.

## Licences and primary interface references

Original fictional content/SVGs are CC0-1.0 according to `data/demo/LICENSE_MANIFEST.json`. No competitor cases/proprietary rubric were copied. Code-package licences are recorded from installed metadata. The MiniLM model card declares Apache-2.0. Torchvision code is BSD-3-Clause; its code licence is not a blanket claim about every upstream image/checkpoint permission. Redis7.4 has [RSALv2/SSPLv1 terms](https://redis.io/legal/licenses/), as described by Redis; retain the selected distribution's terms. Hosting audience and redistribution decisions require the owner's release review.

Checked official interfaces: [FastAPI containers](https://fastapi.tiangolo.com/deployment/docker/), [Next self-hosting](https://nextjs.org/docs/app/guides/self-hosting), [MCP SDK v2.2.0](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/README.md), [Anthropic tool schemas](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools), [SSDLite320](https://docs.pytorch.org/vision/0.23/models/generated/torchvision.models.detection.ssdlite320_mobilenet_v3_large.html), [multilingual MiniLM card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html). GitHub Actions checkout v5 / setup-python v6 / setup-node v6 refs were resolved through the official repository API to immutable commit hashes used in CI.
