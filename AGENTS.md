These AGENTS.md instructions replace all previously provided AGENTS.md instructions.

# MCeLE hackathon demo: agent policy and operating boundaries

## Agent ownership

- GPT-6 Astra is the main agent and owns planning, architecture, integration, final review, user communication, and VM deployment.
- The user explicitly authorizes parallel subagents for independent, bounded work within this task. Do not create separate sidebar tasks.
- Every spawned subagent MUST explicitly use model `gpt-5.6-luna`. Use `fork_turns="none"` or a limited turn count; never a full-history fork that forces model inheritance.
- If Luna or per-subagent model selection is unavailable, report this and continue with Astra. Never silently substitute another model.
- Give every subagent a self-contained assignment with relevant context, exact file ownership, acceptance criteria, and all applicable source-protection and deployment-approval restrictions below.
- Delegate bounded frontend, dataset, backend, documentation, or verification work. Avoid overlapping edits and concurrent deployment operations. Astra reviews and integrates all delegated work.
- Subagents have the same restrictions as the main agent. Delegation never grants deployment approval.

## Authoritative source and workspace

- Initial scaffolding source: live Atlas project `/home/velvux/ChatBotLLM`. Inspect deployed container code/mounts/configuration before copying. Local reference `/Users/elvis/All Projects/ChatBotLLMPrototypeUSMCU` is not authoritative.
- Verified SSH entry point: `ssh velvux@100.98.232.101`. Atlas hostname: `atlas.tail65b4a7.ts.net`. Inspection found Atlas reports Tailscale IP `100.122.223.11`; resolve the discrepancy before binding or documenting access.
- This USB project becomes the source of truth after scaffolding. Edit here and deploy through a reviewed, repeatable allowlist. No untracked VM code edits.
- Use portable project-relative paths. USB is exFAT: keep virtual environments, permission-sensitive dependencies, and caches on a native local filesystem; document their locations. Exclude macOS `._*` and `.DS_Store` metadata from deployments and submission. Runtime services and persistent storage belong on Atlas.
- Do not initialize or publish a new repository until the user says the working demo is ready for that step. Walkthrough and submission packaging are also deferred until requested.

## Protect the existing deployment

- Treat `/home/velvux/ChatBotLLM` as read-only: never edit, overwrite, move, delete, or sync into it.
- Never stop, restart, rebuild, or reconfigure existing application, database, Langfuse, or model containers.
- Never modify/delete existing databases, tables, indexes, volumes, networks, knowledge files, proxy routes, tunnels, DNS, firewall settings, or port assignments.
- No Docker prune commands, broad deletion syncs, or Compose shutdown against existing services.
- Reuse Ollama at `http://192.168.50.212:11434` from Atlas. Do not provision a replacement LLM stack, change model configuration, or download/replace models.
- Preserve chat `qwen3:30b-a3b-instruct-2507-q4_K_M`, embedding `nomic-embed-text`, and vision `qwen2.5vl:7b` unless the user explicitly approves a change.
- Existing Langfuse API use and creation of a separate demo project are allowed; changing its infrastructure or existing project settings is prohibited.
- Never place secrets in prompts, source files, logs, documentation, or the eventual repository. Do not copy production secrets wholesale. Provision only required demo credentials outside tracked files.
- Do not copy the full knowledge base, even temporarily, or its populated vector index. Inspect structure and selectively read examples only as needed. Package only explicitly selected, redistributable articles; label synthetic content.

## Deployment approval and isolation

- Initial inspection is read-only on Atlas. USB implementation is permitted, but first deployment requires the user's approval of a concrete, reviewable configuration.
- Before that approval, prepare destination directory, Compose project and service/container names, ports, CPU/RAM/disk needs, access method, mounts/volumes/networks, credentials plan, isolation checks, resource inventory, and demo-only rollback.
- Inspect current host capacity, occupied ports, original service health, and shared GPU considerations. Avoid disruptive load tests.
- Ask whether attendee access must be public or Tailscale-only before external exposure. Do not change original access routes.
- Use a separate Atlas deployment directory, distinct Compose project, demo-specific names/network/volumes, and dedicated demo database/vector index. Keep database and backend ports internal where practical.
- Deployment must use an explicit file allowlist or exclusions, no broad deletion, and a destination guard rejecting the original path. Inspect copied scripts/Compose for hardcoded production names, paths, external volumes, or destructive operations before running anything.
- Missing demo configuration must fail clearly. Ingestion must validate that it can target only demo storage, never default to original resources.
- After the first isolated deployment is approved, routine updates are allowed only within that approved scope. Any required change to an existing service must stop for explanation and user direction.
- Verify both original and demo health, end-to-end demo behavior/traces, and independence from workstation/USB. Maintain inventory and rollback targeting only demo-created resources.

## Implementation sequence and scope decisions

1. Inspect live integrations and deployment, then copy only allowlisted application source; exclude history, secrets, generated files, backups, data, and the original corpus.
2. Preserve working backend/model/Langfuse integrations; configure isolated demo storage and strict configuration guards.
3. Prepare/review deployment; after approval, deploy a minimally changed baseline with tiny explicitly selected or synthetic data and verify Langfuse traces.
4. Add server-controlled profiles, explicit role access, course context, curated data, necessary memory changes, then ticket handoff last.
5. Repository, final walkthrough, and submission packaging wait for the user's readiness signal.

- MCeLE is the ecosystem; Moodle is optional. Select scenarios, course/system mappings, article coverage, and permission matrix with the user. Do not invent course facts or integrations.
- Selected roles: Student; UI Instructor with underlying role Adjunct Faculty; Academics Officer (AO); Training Manager; Regional Director. AO is an additional role. Regional Director is a presentation placeholder without a support scenario. No automatic role inheritance. See `docs/demo-decisions.md` for selected scenarios and outstanding content/mapping decisions.
- Public demo access is required. This access decision does not grant first deployment approval or permission to change any existing access route.
- Profile selection simulates identity, not production authentication. Resolve selected IDs against server-controlled records. Isolate sessions, caches, retrieved context, and history between profiles.
- Enforce explicit role access before retrieval content reaches the LLM, including candidate/routing/follow-up/fallback search, citations, previews, and any other knowledge exposure. Missing access metadata means deny.
- Keep course relevance distinct from course access. Explicit course selection takes priority over profile hints; clarify conflicts. Course changes must not retain misleading system assumptions.
- Curated target is roughly 10–15 articles, final count/coverage decided together. Include stable ID, title, area, allowed roles, optional course scope, content, and provenance. Keep sources here and ingestion reproducible.
- Preserve traces for retrieval, routing, model calls, and selections. Prefer a separate project in existing Langfuse and add role/course/system/filter metadata without secrets.
- Ticket page and fields are pending from the user. Inspect supported prefill when supplied and implement last; do not submit tickets without authorization.
- Memory architecture should remain simple until ticket requirements are known. Current source uses browser history and separate short retrieval/generation windows; see inspection report.
- Add focused checks for role filtering, profile isolation, course changes, selected-only indexing, and traces. Document simulations, real dependencies, setup/deployment workflow, and infrastructure needed by judges outside the private VMs.

## Current checkpoint

Current release `150982c95159b944` is running on the isolated Atlas demo services. Original app health and 315 chunks are unchanged. First deployment/public tunnel approval was granted on 2026-09-14; routine updates within the reviewed isolated resources remain approved. Limits: combined 2.75 CPUs / 2.25 GiB RAM. Public URL remains https://domain-heater-nelson-tours.trycloudflare.com (random Quick Tunnel; may change on restart).

Five server-controlled profiles, four approved articles, task-specific course mappings, role-filtered retrieval, and server-side session transcripts are implemented. 55 offline tests and serial real scenario checks passed, including synthetic screenshot recognition and dedicated Langfuse traces. Article record/editorial metadata is not embedded. The two synthetic baseline articles are retired from demo storage and excluded from the current release; no original corpus/data/secrets were copied. Separate Langfuse project `cmu1njwr40003l808bk5ak05x` is configured with private demo keys on Atlas.

IMPORTANT user correction: course alone does not determine system. 5500, CSC and EWS course content is Moodle, enrollment MCeLE. CDETBAIC01 Basic AI Course is MCeLE for both. CYBERM0000 content is MCeLE. 6800 enrollment is MCeLE; course content platform remains unconfirmed. The course field accepts codes/names; unknown mappings and unclear tasks require clarification. See `docs/profiles-courses-and-access.md` for the current policy, superseding older single-platform assumptions.

Current operational articles: Student MCELE-LAUNCH-001 (exact sts1 error plus MCeLE course-content context; excludes Moodle); Instructor/Adjunct Faculty MOODLE-COPY-002 (permission guidance); Academics Officer MOODLE-COPY-001 (steps, tutorial, MClearn reminder); Training Manager MCELE-ECDEP-001 (MCeLE enrollment Recommend/Deny, only5500/6800). No role inheritance; Regional Director has no articles. Sessions are immutable to profile, full transcripts remain in demo Postgres, and course/task changes clear model history and evidence while retaining contextualized turns for the future ticket handoff.

User's actual screenshot still needs checking when supplied. Ticket page/fields are pending and implementation remains last. Final walkthrough, repository creation, redistribution review and submission packaging wait for the user's readiness signal; no Git repository has been initialized. See `docs/curated-validation.json`, `docs/atlas-deployment-record.json`, `docs/deployment-review.md`, and `README.md` for current validation, inventory, workflow, and rollback. `docs/baseline-validation.json` and `docs/initial-inspection.md` are historical snapshots.

## Grounding and access checkpoint — 2026-09-16

Instructor and AO copying answers now reproduce only their permission-filtered curated excerpts. Generated HTTP links for other articles must exactly match a permitted source; unsupported links trigger source-excerpt fallback. Blanket automatic citations were removed. Expanded serial scenarios, including Instructor grounding and both AO links, passed on release `150982c95159b944`. Use `scripts/deploy.py --apply --transport tailscale` with the existing approval flag from this Mac. Atlas is confirmed at `100.122.223.11`; the user added the needed Tailscale SSH rule. GitHub destination is `elvisinthecloud/HackathonChatbotLLM`, with push deferred until the project is completely finished.

## Repository checkpoint — 2026-09-16

The user explicitly requested uploading the current project to `https://github.com/elvisinthecloud/HackathonChatbotLLM.git`, superseding the earlier Git deferral. The destination is public. Review source for credentials and exclude generated files, macOS metadata, and unselected-source discovery notes. Preserve article provenance; do not invent a third-party redistribution license. Ticket handoff and real screenshot verification remain unfinished.

## USB recovery — 2026-09-16

The USB volume is unavailable. The user requested saving the project to Desktop. This recovery folder contains the exact 34-file deployed source snapshot plus recovered documentation/tests; consult `recovery/RECOVERY.md` before assuming completeness. Recovery made no Atlas changes and did not copy secrets or raw conversations. Use this Desktop folder for further local work; do not require the failed USB.
