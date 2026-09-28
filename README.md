# MCeLE Support Demo — recovered project

Recovered to this Desktop folder on 2026-09-16 after the USB drive disappeared. This README is a new recovery guide, not an exact restoration of the previous README. See [the recovery report](recovery/RECOVERY.md) for completeness and missing files.

## Verified application source

All 34 files from deployed release `150982c95159b944` were read from the isolated deployment host demo and verified against its SHA-256 release manifest. This includes the backend, frontend, schema, guarded deployment scripts, four curated articles, and synthetic screenshot. No production corpus, databases, runtime credentials, or raw conversations were copied. the deployment host was not modified.

The demo provides five simulated profiles with explicit role filtering, task-specific course mappings, server-side transcripts, and Langfuse traces. Instructor and AO copying answers use their permitted excerpts. Unsupported generated HTTP links trigger a source-excerpt fallback. The original deployment was last verified healthy with 315 chunks; the demo has four approved article chunks.

Public demo: https://demo.example.invalid

Repository destination: https://github.com/elvisinthecloud/HackathonChatbotLLM

This is the recovered source checkpoint prepared for GitHub on 2026-09-16. The earlier USB upload failed during staging; GitHub Write access has since been granted. Ticket handoff and verification of the user's actual course-error screenshot remain unfinished. Article provenance is retained; no third-party redistribution license is inferred.

## Working from this recovery

Use this folder as the recovered source snapshot. Python 3.12 is required. Keep virtual environments and credentials outside the project. The former temporary virtual environment is no longer present. Install `backend/requirements.lock` into a fresh environment before running application tests.

The running the deployment host deployment is independent of the workstation. Its existing demo-only credentials remain on the deployment host. The original `/home/demo/ChatBotLLM` remains strictly read-only. Do not copy or publish the runtime environment file.

The deployment workflow supports `python scripts/deploy.py --plan --transport tailscale`. Applying updates still requires the established approved demo-only scope and `MCELE_DEMO_DEPLOY_APPROVED=1`. Recovery itself did not deploy anything.

Configuration template: `config/runtime.env.example`. Current deployment records: `docs/atlas-deployment-record.json` and `docs/curated-validation.json`. Complete role/course policy: `docs/profiles-courses-and-access.md`. Historical handoff: `recovery/MCeLE_Hackathon_Demo_Handoff.md`.

## Private deployment configuration

Public files use reserved `.invalid` example hosts. They are not working endpoints.
Set the existing Ollama origin in the private runtime file using `OLLAMA_BASE_URL`;
Compose forwards that value and the backend rejects missing or placeholder origins.
Existing runtime files already containing the endpoint need no credential changes.

Configure a local SSH alias named `mcele-demo` outside this repository, or set
`MCELE_DEMO_SSH_HOST` privately. For `--transport tailscale`, set that variable to
the approved Tailscale SSH target; OpenSSH aliases apply only to `--transport ssh`.
The remote account's home directory determines the fixed demo root
`~/mcele-hackathon-demo` and runtime path
`~/.config/mcele-hackathon-demo/runtime.env`.
Before using the deployment or verification tools, record the approved server's
hostname in `~/.config/mcele-hackathon-demo/hostname` on that server (outside Git).
The tools compare it to the current hostname before operating. Keep the original
application read-only; all existing demo identity, resource, and path guards apply.

Recovery documents and historical inventories have been sanitized. Their example
addresses and account paths must not be used for deployment. Historical hash
manifests describe the original recovery, not the sanitized files. Never commit
private runtime files, host identity files, SSH configuration, or fresh operational
inventories. This repository cleanup does not modify the running deployment.
