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

- Initial scaffolding source: live deployment host project `/home/demo/ChatBotLLM`. Inspect deployed container code/mounts/configuration before copying. Local reference `/Users/elvis/All Projects/ChatBotLLMPrototypeUSMCU` is not authoritative.
- Verified SSH entry point: `ssh demo@demo-host.example.invalid`. the deployment host hostname: `demo-host.example.invalid`. Inspection found the deployment host reports Tailscale IP `demo-host.example.invalid`; resolve the discrepancy before binding or documenting access.
- This USB project becomes the source of truth after scaffolding. Edit here and deploy through a reviewed, repeatable allowlist. No untracked VM code edits.
- Use portable project-relative paths. USB is exFAT: keep virtual environments, permission-sensitive dependencies, and caches on a native local filesystem; document their locations. Exclude macOS `._*` and `.DS_Store` metadata from deployments and submission. Runtime services and persistent storage belong on the deployment host.
- Do not initialize or publish a new repository until the user says the working demo is ready for that step. Walkthrough and submission packaging are also deferred until requested.

## Protect the existing deployment

- Treat `/home/demo/ChatBotLLM` as read-only: never edit, overwrite, move, delete, or sync into it.
- Never stop, restart, rebuild, or reconfigure existing application, database, Langfuse, or model containers.
- Never modify/delete existing databases, tables, indexes, volumes, networks, knowledge files, proxy routes, tunnels, DNS, firewall settings, or port assignments.
- No Docker prune commands, broad deletion syncs, or Compose shutdown against existing services.
- Reuse Ollama at `http://ollama.example.invalid:11434` from the deployment host. Do not provision a replacement LLM stack, change model configuration, or download/replace models.
- Preserve chat `qwen3:30b-a3b-instruct-2507-q4_K_M`, embedding `nomic-embed-text`, and vision `qwen2.5vl:7b` unless the user explicitly approves a change.
- Existing Langfuse API use and creation of a separate demo project are allowed; changing its infrastructure or existing project settings is prohibited.
- Never place secrets in prompts, source files, logs, documentation, or the eventual repository. Do not copy production secrets wholesale. Provision only required demo credentials outside tracked files.
- Do not copy the full knowledge base, even temporarily, or its populated vector index. Inspect structure and selectively read examples only as needed. Package only explicitly selected, redistributable articles; label synthetic content.

## Deployment approval and isolation

- Initial inspection is read-only on the deployment host. USB implementation is permitted, but first deployment requires the user's approval of a concrete, reviewable configuration.
- Before that approval, prepare destination directory, Compose project and service/container names, ports, CPU/RAM/disk needs, access method, mounts/volumes/networks, credentials plan, isolation checks, resource inventory, and demo-only rollback.
- Inspect current host capacity, occupied ports, original service health, and shared GPU considerations. Avoid disruptive load tests.
- Ask whether attendee access must be public or Tailscale-only before external exposure. Do not change original access routes.
- Use a separate the deployment host deployment directory, distinct Compose project, demo-specific names/network/volumes, and dedicated demo database/vector index. Keep database and backend ports internal where practical.
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

Current release `150982c95159b944` is running on the isolated deployment host demo services. Original app health and 315 chunks are unchanged. First deployment/public tunnel approval was granted on 2026-09-14; routine updates within the reviewed isolated resources remain approved. Limits: combined 2.75 CPUs / 2.25 GiB RAM. Public URL remains https://demo.example.invalid (random Quick Tunnel; may change on restart).

Five server-controlled profiles, four approved articles, task-specific course mappings, role-filtered retrieval, and server-side session transcripts are implemented. 55 offline tests and serial real scenario checks passed, including synthetic screenshot recognition and dedicated Langfuse traces. Article record/editorial metadata is not embedded. The two synthetic baseline articles are retired from demo storage and excluded from the current release; no original corpus/data/secrets were copied. Separate Langfuse project `REDACTED_DEMO_PROJECT_ID` is configured with private demo keys on the deployment host.

IMPORTANT user correction: course alone does not determine system. 5500, CSC and EWS course content is Moodle, enrollment MCeLE. CDETBAIC01 Basic AI Course is MCeLE for both. CYBERM0000 content is MCeLE. 6800 enrollment is MCeLE; course content platform remains unconfirmed. The course field accepts codes/names; unknown mappings and unclear tasks require clarification. See `docs/profiles-courses-and-access.md` for the current policy, superseding older single-platform assumptions.

Current operational articles: Student MCELE-LAUNCH-001 (exact sts1 error plus MCeLE course-content context; excludes Moodle); Instructor/Adjunct Faculty MOODLE-COPY-002 (permission guidance); Academics Officer MOODLE-COPY-001 (steps, tutorial, MClearn reminder); Training Manager MCELE-ECDEP-001 (MCeLE enrollment Recommend/Deny, only5500/6800). No role inheritance; Regional Director has no articles. Sessions are immutable to profile, full transcripts remain in demo Postgres, and course/task changes clear model history and evidence while retaining contextualized turns for the future ticket handoff.

User's actual screenshot still needs checking when supplied. Ticket page/fields are pending and implementation remains last. Final walkthrough, repository creation, redistribution review and submission packaging wait for the user's readiness signal; no Git repository has been initialized. See `docs/curated-validation.json`, `docs/atlas-deployment-record.json`, `docs/deployment-review.md`, and `README.md` for current validation, inventory, workflow, and rollback. `docs/baseline-validation.json` and `docs/initial-inspection.md` are historical snapshots.

## Grounding and access checkpoint — 2026-09-16

Instructor and AO copying answers now reproduce only their permission-filtered curated excerpts. Generated HTTP links for other articles must exactly match a permitted source; unsupported links trigger source-excerpt fallback. Blanket automatic citations were removed. Expanded serial scenarios, including Instructor grounding and both AO links, passed on release `150982c95159b944`. Use `scripts/deploy.py --apply --transport tailscale` with the existing approval flag from this Mac. the deployment host is confirmed at `demo-host.example.invalid`; the user added the needed Tailscale SSH rule. GitHub destination is `elvisinthecloud/HackathonChatbotLLM`, with push deferred until the project is completely finished.

## Repository checkpoint — 2026-09-16

The user explicitly requested uploading the current project to `https://github.com/elvisinthecloud/HackathonChatbotLLM.git`, superseding the earlier Git deferral. The destination is public. Review source for credentials and exclude generated files, macOS metadata, and unselected-source discovery notes. Preserve article provenance; do not invent a third-party redistribution license. Ticket handoff and real screenshot verification remain unfinished.

## USB recovery — 2026-09-16

The USB volume is unavailable. The user requested saving the project to Desktop. This recovery folder contains the exact 34-file deployed source snapshot plus recovered documentation/tests; consult `recovery/RECOVERY.md` before assuming completeness. Recovery made no the deployment host changes and did not copy secrets or raw conversations. Use this Desktop folder for further local work; do not require the failed USB.

## Network privacy — 2026-09-28

Network identifiers in historical notes below are sanitized examples, not deployment instructions. Use the private configuration described in README.md. Do not put actual hostnames, tailnet addresses, home LAN addresses, runtime environment files, or operational inventories into Git. The recovered GitHub checkout on the native Mac filesystem supersedes the unavailable USB workspace.

## Guided support checkpoint — 2026-09-29

The local `codex/integrate-intake-and-articles` branch has nine selected articles and
guided support implemented in `backend/troubleshooting.py` and `backend/rag.py`.
Server session context stores pending questions, user-confirmed facts and completed
steps. Error, course, task and topic changes reset active guidance and model history.
Role filtering runs before each source use. Support facts and links are copied from
the selected approved article; the existing model can select a passage ID but cannot
write support facts. The frontend offers optional quick replies through its existing
send path. See `docs/guided-troubleshooting.md` for offline coverage and bounded limits.

The VM is unavailable. These changes have offline checks only; no live model,
database, deployment or trace parity has been established for this checkpoint.
Continue in the recovered native checkout, not the missing USB. Five source
candidates were selected from the user's Confluence ZIP for login and course
access, using the index and selective in-place HTML reads. Their references and
source audience tags are in `docs/knowledge-base-next-batch.json`; they are not
indexed. Do not copy the full corpus. Review access metadata and routing with each
addition. Legacy dynamic clarification options and the manual bucket selector have
been removed. Quick replies require the matching question in the current response;
an error-change button requires known error evidence.


## Reviewed access batch — 2026-09-30

The native local checkout now has fifteen curated articles: the nine existing
sources plus six selectively adapted Confluence sources for login, CAC,
credential recovery, enrolled-course launch, Moodle browser access and app access.
The human reviewed all six for everyone; each grants all five seeded roles
explicitly. Existing role-specific management and enrollment grants remain
independent. Source references and decisions are in
`docs/knowledge-base-next-batch.json`; the source ZIP was not modified or extracted.
The existing nine-file upload archive is a prior snapshot and remains unchanged.

`backend/access_support.py` provides section-specific guided support and remembers
Moodle app/browser choice in server context outside the short history window.
Phone alone requires method clarification; method/course/topic switches reset old
progress. Entry point is separate from content platform; a failed MCeLE-to-Moodle
handoff goes to Instructor-Led Courses in the left navigation. Missing Moodle tiles,
broken materials/activities and created-course problems use Student Support Help
Desk option 3. The existing CSC-specific escalation remains independently scoped.
The existing CSC navigation wording was corrected to the left navigation menu.
CYBERM0000 remains biennial; the bounded export audit found generic annual language
but no inspected article explicitly asserting annual CYBERM0000 training.
All changes are local/offline. No VM/database indexing/model/deployment was run.
Model configuration and the six-exchange/12,000-character history limits are unchanged.

## Retrieval evaluation preparation — 2026-09-30

`scripts/evaluate_retrieval.py` and its synthetic cases separate a pure routing
audit from optional actual-model cosine diagnostics over the six-source access
subset and all fifteen selected sources. The default audit makes no service calls:
42 of 46 expected routes match; four natural paraphrases prompt extra clarification.
Thirty-five source turns have a single production route candidate, so this does
not establish retrieval competition accuracy. Eight focused harness checks and
the packaging check passed. Live embedding mode is bounded, sequential and guarded
to the approved host; it preserves `nomic-embed-text`, makes no database writes
or chat calls, and is not the production pgvector/API path. No live ranking was run.
The runner and synthetic cases are included in the release allowlist (50 files).

Five additional overlapping sources are proposed in
`docs/retrieval-competition-next-batch.json`, pending human source/access review:
Unlock Your Account, Associate CAC to Account, Finding and Registering for Courses,
View Enrolled Courses, and Reactivating a Disabled Account. A title-only Moodle
Troubleshooting parent was excluded. No new source grants, curation or indexing
occurred. Conversational/model changes remain to be assessed against this baseline.

## Follow-up article review — 2026-10-02

Tailscale SSH access to the VM was verified again through a workstation-only private
SSH alias; no VM services, storage, model configuration or deployment was changed.
Live retrieval/model evaluation remains pending.

Four of the five proposed articles are reviewed for all five roles in their stated
scopes: account unlock, CAC association, own non-PME course enrollment, and own
course listings/status/records. The last article, inactivity-disabled account
reactivation, awaits audience and self-service-versus-Help-Desk confirmation.
See `docs/retrieval-competition-next-batch.json` for authoritative decisions.
The new batch is not integrated or indexed; the manifest remains fifteen articles.
CAC association's nested credential-recovery/resume behavior is approved design,
not implemented; detailed new-account creation needs separate source review.

The user confirmed Student Dashboard > My Courses in the left navigation for all
roles using their own learner courses. The existing curated general launch article
now uses that navigation instead of My Active Courses; source validation and the
25 focused access tests passed offline. Reviewed JSON drafts for course finding/
enrollment and course viewing are in `docs/article-drafts/`. Available request forms
open through My Courses > Launch or View > Enrollment > Overview > Request; use
plain wording such as "open the form". Opening a form does not mean it was submitted
or approved. View reviews completed content without re-enrollment. The optional
Portal Home widget is omitted from the viewing draft pending label confirmation.

The user subsequently declined Reactivating a Disabled Account. It is excluded
from the batch, and the existing Help Desk route for disabled/deactivated accounts
remains. The four remaining article reviews are complete and approved in their
explicit scopes; local batch integration and indexing remain pending. Do not add
the declined self-service reactivation flow or assume a replacement fifth article.

## Live integration and synthetic testing — 2026-10-02

Release `655d8389af771862` is running in the previously approved isolated demo.
The selected manifest contains nineteen articles indexed as 24 chunks. Original
frontend/backend/Langfuse health and the original 315 chunks are unchanged. All
55 release files were checked against local source; model identities, resource
limits, the original app, and existing access routes were preserved.

The four approved follow-up articles are curated, integrated, and indexed. CAC
association retains its parent goal through credential recovery and resumes after
completion. The declined disabled-account article remains excluded; detailed
account creation still needs separate source/access review. This checkpoint
supersedes earlier notes describing the VM or these integrations as unavailable.

Three Luna agents ran thirteen baseline conversations (47 chat turns), eight
targeted replays (49 turns), and root ran two final checks (six turns). All main
chat calls returned HTTP 200. The initial unpaced attempts produced thirteen
HTTP 429 replies; pacing was added only to the test client. An extra lockout turn
and a separate capped attempt are preserved as protocol deviations. This was
serialized synthetic testing, not a capacity benchmark.

All 47 baseline traces were inspected; two had Qwen passage-selection calls.
Guidance remains primarily server-controlled and source-rendered, so these results
do not establish freely generated LLM conversation quality. Live embedding
diagnostics ranked the expected article first in 38/48 source questions and in
the top three in 48/48; those broad-pool rankings are distinct from API accuracy.
The fixed routing audit matched 53/53; 150 Python and six JavaScript checks passed.

Remaining failures include repeated catalog steps after natural completion
reports, retaking a completed course being answered with listing navigation, and
extra clarification for some negated CAC/PIN guesses. Keep these partial outcomes
visible; allowed citations alone do not establish a useful reply. Sanitized
findings are in `docs/synthetic-testing-summary.json`. Full private synthetic
transcripts, trace evidence and the HTML report stay outside Git. No full corpus,
private network identifiers, session tokens or runtime secrets were committed.

## Model interpretation checkpoint — 2026-10-02

At the human's explicit request, GPT-6 Astra on High planned and implemented the
intent/progress change. Release `eb5a3023f35c3283` is deployed in the existing
approved isolated demo. All 56 allowlisted files match local source; nineteen
approved articles remain indexed as 24 chunks. Original frontend/backend/Langfuse
health and the original 315 chunks are unchanged. Existing models, resource limits,
access routes and source grants were preserved.

Meaningful support turns now call the existing Qwen model once for bounded intent,
explicit access-method evidence, source-unit selection and reported progress.
The server validates every component, rechecks profile/course/source permissions,
owns state transitions and renders approved source facts/links. Generic completion
requires a pending step; symptoms, negative and hypothetical reports cannot confirm
completion. Unanswered Moodle method questions remain pending through vague Done
replies. Role claims do not change the selected profile.

The final serialized replay contains sixteen conversations and 37 HTTP 200 chat
turns. All 37 traces show one Qwen interpretation generation, no fatal rejections
and no citation/access inconsistencies. A duplicate progress report was discarded
independently. Manual review passed the selected progress, correction, retake,
request-boundary, role and course cases. Earlier failed revisions remain preserved
as historical evidence. The final source passed 199 Python and six JavaScript
checks. See `docs/model-interpretation-validation.json` and
`docs/guided-troubleshooting.md`; private exact transcripts and the HTML report
remain outside Git. These are bounded synthetic text API checks, not full-corpus,
real-user, screenshot, frontend end-to-end or concurrent-user accuracy claims.


## LLM-selected article passages checkpoint — 2026-10-03

The human requested GPT-6 Astra on Low for implementation and several GPT-6.1
Sol agents on Medium for live synthetic evaluation; this superseded prior model
preferences for this task. The human approved letting the LLM select relevant
article passages while quoting factual guidance exactly, with natural questions
and follow-ups. Inform the human before substantial rewrites and obtain approval
before future foundational architecture changes.

Release `7ee88b7a8d5edc3c` is deployed in the existing approved isolated demo.
Qwen reads actual conversation history and bounded memory, selects canonical
passages or a bounded clarification act, and performs a separate applicability
review with at most one repair. Generated factual prose is not rendered. Scope,
section conditions and citations accompany selected source text. Narrow reviewed
coverage checks decline unsupported PIN-reset, automatic-denial and failed
recovery-page inferences; these checks are not exhaustive intent understanding.

Server-owned demo profiles, explicit role grants, course/platform constraints and
fresh indexed source metadata remain authoritative. Retained-source lookup cannot
bypass current indexed authorization. No source grants or model identities changed.
All 57 allowlisted runtime files match the evaluated source. Nineteen articles are
indexed as 24 chunks; original service health and 315 original chunks are unchanged.

Three Sol reviewers evaluated nineteen final synthetic conversations (54 live
text API turns): seven pass, twelve partial, zero fail. Sixteen conversations replay
previous inputs; three held-out conversations add adaptive second turns. All 54
responses returned HTTP 200, and all 54 traces were audited: 115 model generations,
zero observed source-access inconsistencies. Reviewers found no invented factual
guidance in this bounded replay. This does not establish general accuracy or
correct applicability: one manual-unlock reply preserved a before-wait condition
after the user reported waiting. Other partials include broad repeated passages,
unnecessary questions, skipped enrollment navigation, reviewer false rejections,
generic fallbacks and a historical course mention blocking an explicit switch.

Current checks: 249 Python and six JavaScript tests passed. Sanitized evidence and
limitations are in `docs/llm-behavior-validation.json`. The separate HTML report
includes exact final and historical synthetic conversations; raw bearer tokens,
trace IDs and private operational details remain outside Git. Prior free-prose
revisions produced unsupported facts even with model review and are retained as
historical failures. Text API tests were serialized; no browser app flows, real
users, screenshot understanding, concurrent-user behavior or unseen corpus were
validated. Demo role selection is not production authentication.


## Understanding before guidance checkpoint — 2026-10-03

The human approved the foundational understanding-before-guidance redesign and
execution after the vague course-help screenshot exposed an article dump. Astra
on Low implemented it; Sol 6.1 on Medium independently reviewed live synthetic
conversations. The parent reviewed, integrated, tested and deployed. Continue to
inform the human before substantial rewrites and obtain approval before future
foundational changes; factual guidance remains exact approved article text.

Release `95476e195b49ce1b` is running in the already approved isolated demo. Qwen
identifies the goal before source retrieval; unresolved goals ask a bounded neutral
question with zero retrieval. Finer source passages, validated progress, exclusive
guidance/clarification modes and a single applicability verdict reduce article
dumps and false rejections. Role grants, models and nineteen articles/24 chunks
are unchanged. All 57 runtime files match the evaluated source. Original service
health and 315 chunks are unchanged. No Git commit or push occurred.

The final release review has twelve conversations and 34 live API turns: six pass,
three partial, three fail. Eight cases replay earlier adaptive inputs; four role
and course cases are fresh adaptive conversations. All 34 traces were audited
(93 Qwen generations), with zero observed source-access inconsistencies. A
separate two-turn public mobile browser check verifies the reported vague opener.
Offline validation: 280 Python and six JavaScript tests passed.

Keep the failures visible: an explicit disabled-account switch misses available
Help Desk guidance; a CAC recovery detour initially provides a non-actionable
reference; a Student requesting Training Manager instructions gets an irrelevant
repeated screen/error question, although access restrictions hold. Partials include
omitted navigation, a repeated eligibility check and an omitted request-form scope
limitation. No claim of consistently successful troubleshooting is warranted.

A later focused-query experiment (`236e4a7026f78e4d`) removed useful workflow
context and regressed certificate, Catalog View and request-form answers. It was
rejected and the exact fully reviewed source restored. Its failures remain in the
private report; do not silently reapply that experiment. See
`docs/conversation-redesign-validation.json` for sanitized evidence. The HTML review
and raw synthetic records remain outside Git. No real-user, vision-understanding,
concurrent-load or unseen-corpus validation is claimed.

## Unified planner redesign checkpoint — 2026-10-03

The human approved a foundational redesign after the launch-error screenshot
showed repeated goal questions and generic instructions. Astra on Low implemented
the planner and reply formatting; three Sol 6.1 Medium agents independently ran
bounded real-VM suites. The parent integrated, replayed exact inputs and audited
traces; a Sol reviewer and parent assessed the final responses. Future foundational
changes still require approval; substantial rewrites must be announced first.

Release `724fd72f045deb9f` is the current isolated development demo. One planner
chooses clarification, retrieval, exact passages or bounded source/role limits.
Goal, obstacle, parent goal and user-reported progress are separate memory fields.
The wire envelope places assessment and move before source selection. State uses
exact user quote anchors; model assessment is never rendered or treated as a fact.
There are at most two source searches and one structural repair per turn. The active
path no longer invokes the former understanding/draft/semantic-review chain. Those
helpers remain for legacy tests. Explicit role grants, course constraints and fresh
source metadata remain server-controlled; sources/history cannot grant authority.

Numbered replies retain source step numbers and render as spaced lists. The former
six-passage cutoff is now sixteen, allowing the complete eight-step STS1 procedure.
No factual source wording, article grants or model identities changed. All 57 runtime
files match the evaluated source. Nineteen articles are indexed as 24 chunks;
original frontend/backend/Langfuse health and 315 original chunks remain unchanged.
306 Python and nine JavaScript tests pass. No Git commit or push occurred.

Behavior acceptance FAILED overall: final fixed replay has 13 conversations,
34 live API turns, one pass, three partial and nine failures. All 34 HTTP responses
succeeded and their traces were audited (40 chat generations), with zero observed
source-access inconsistencies. A separate five-turn public mobile browser check
passed the exact screenshot sequence and numbered-list layout. These are synthetic
text tests, not image understanding, real users, capacity or unseen-corpus validation.
The screenshot error survives “Launch it”; STS1 restart/relaunch steps are complete.
Covered username recovery, certificate facts, Catalog View, request boundaries,
CAC recovery/resumption, disabled-account corrections and role-permission followups
still receive unnecessary questions or generic failures. Access safety alone is not
conversational success. Do not represent this release as production-ready or as a
successful overall behavior acceptance.

Early failed candidates and a rejected prompt-wording experiment are retained in
the private HTML review. Restoring wording did not restore every prior success;
these runs do not establish a single causal explanation for output variation.
`docs/planner-redesign-validation.json` is the sanitized final record. Full private
transcripts, tokens, operational details and the HTML review remain outside Git.
The human chose to review current-model results before choosing the comparison
setup. No alternative model has been selected, installed or tested. Preserve the
same sources, grants, inputs and factual-rendering contract for that comparison.


## Corpus growth target — 2026-10-03

The human specified an eventual total of 200–300 articles. Carry this target into
future design, model selection and acceptance; nineteen-article success alone is
insufficient. Keep model evidence and catalog exposure bounded as the collection
grows. Preserve explicit article-level role grants, course/system scope and
source-verbatim factual guidance. Prefer reviewed metadata-driven ingestion over
new article-specific conversation branches. Evaluate overlapping and irrelevant
articles, permission boundaries, retrieval quality, usefulness and latency, and
validate updates/retirement. These are future design implications; the larger
corpus has not been selected, approved, ingested or tested. Do not bulk-copy the
original knowledge base or change grants based on this size target. The pending
model comparison remains the next controlled experiment after the user reviews
the current-model results.
