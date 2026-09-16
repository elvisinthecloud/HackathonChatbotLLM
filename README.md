# MCeLE Support Demo — recovered project

Recovered to this Desktop folder on 2026-09-16 after the USB drive disappeared. This README is a new recovery guide, not an exact restoration of the previous README. See [the recovery report](recovery/RECOVERY.md) for completeness and missing files.

## Verified application source

All 34 files from deployed release `150982c95159b944` were read from the isolated Atlas demo and verified against its SHA-256 release manifest. This includes the backend, frontend, schema, guarded deployment scripts, four curated articles, and synthetic screenshot. No production corpus, databases, runtime credentials, or raw conversations were copied. Atlas was not modified.

The demo provides five simulated profiles with explicit role filtering, task-specific course mappings, server-side transcripts, and Langfuse traces. Instructor and AO copying answers use their permitted excerpts. Unsupported generated HTTP links trigger a source-excerpt fallback. The original deployment remains healthy with 315 chunks. Isolated hackathon release `fab13e75b00fb0ab` contains seven curated articles plus two retrieval-only AO routing embeddings.

The `codex/article-dataset-expansion` work expands the curated hackathon dataset to seven source-supported articles. It adds separate AO stuck-copy troubleshooting, a Training Manager Enrollment Report procedure, and Student repeat-course RRC guidance. CSC access and EPME-after-MOL authoring records remain outside the dataset until their stated source decisions are resolved. See [the article expansion status](docs/article-expansion-status.md) and [live validation record](docs/article-expansion-validation.json).

Public demo: https://domain-heater-nelson-tours.trycloudflare.com

Repository destination: https://github.com/elvisinthecloud/HackathonChatbotLLM

This is the recovered source checkpoint prepared for GitHub on 2026-09-16. The earlier USB upload failed during staging; GitHub Write access has since been granted. Ticket handoff and verification of the user's actual course-error screenshot remain unfinished. Article provenance is retained; no third-party redistribution license is inferred.

## Working from this recovery

Use this folder as the recovered source snapshot. Python 3.12 is required. Keep virtual environments and credentials outside the project. The former temporary virtual environment is no longer present. Install `backend/requirements.lock` into a fresh environment before running application tests.

The running Atlas deployment is independent of the workstation. Its existing demo-only credentials remain on Atlas. The original `/home/velvux/ChatBotLLM` remains strictly read-only. Do not copy or publish the runtime environment file.

The deployment workflow supports `python scripts/deploy.py --plan --transport tailscale`. Applying updates still requires the established approved demo-only scope and `MCELE_DEMO_DEPLOY_APPROVED=1`. Recovery itself did not deploy anything.

Configuration template: `config/runtime.env.example`. Current deployment records: `docs/atlas-deployment-record.json` and `docs/curated-validation.json`. Complete role/course policy: `docs/profiles-courses-and-access.md`. Historical handoff: `recovery/MCeLE_Hackathon_Demo_Handoff.md`.
