# MCeLE Support Hackathon Demo

This project is an isolated, role-aware support chatbot built for a hackathon demonstration. It uses a small curated knowledge base, embedding retrieval, explicit role permissions, and cited answers to show how MCeLE and Moodle support guidance can be delivered safely.

## Demo scenarios

The curated dataset contains nineteen selected articles, indexed in the isolated VM demo. The original nine scenarios are:

1. Student — troubleshoot the approved MCeLE course-launch error.
2. Instructor / Adjunct Faculty — request permission to copy a Moodle course.
3. Academics Officer — copy a Moodle course.
4. Training Manager — recommend or deny an ECDEP seminar enrollment request.
5. Academics Officer — troubleshoot a slow or stuck Moodle course copy.
6. Student — access CSC and troubleshoot a missing Moodle enrollment.
7. Student — check EPME course eligibility and enrollment requirements.
8. Training Manager — verify a Marine's enrollment status.
9. Student — determine whether a completed course can earn Reserve Retirement Credits again.

The earlier nine-article upload snapshot is in [`hackathon-dataset`](hackathon-dataset), with its [`hackathon-dataset.zip`](hackathon-dataset.zip). That archive contains nine `.txt` files with only an Article record and Knowledge content; internal editorial and retrieval notes are excluded.

The six reviewed additions cover MCeLE login, CAC login problems, credential recovery, enrolled-course launch, Moodle browser access, and Moodle app access. All five seeded roles have explicit access to these six articles. Source provenance and user-confirmed navigation/escalation changes are preserved in the runtime JSON files. Four further reviewed additions cover temporary account unlock, CAC association, own non-PME course enrollment/request forms, and own courses/records. All five roles have explicit guidance access in these scopes. The existing upload snapshot has not been rebuilt for these additions.

## Pipeline

1. The server resolves the selected demo profile. Chat messages cannot change its role or supply trusted history. An explicit course selection remains authoritative.
2. The current Qwen model interprets the user report independently of articles. It proposes exact user-grounded facts and explicit corrections/retractions. The server validates provenance and reconciles active facts once per turn, retaining a bounded supersession history.
3. PostgreSQL vector and lexical searches retrieve a bounded shortlist under explicit role grants. Course, platform, method and error conditions are checked separately as applicability. Unknown applicability does not hide authorized source conditions from the model.
4. A second model call chooses useful exact passages or one purposeful clarification. The server validates evidence IDs, applicability and quote anchors. Two normal calls share at most one repair; there is no extra model reviewer on every turn.
5. The server renders canonical article facts, qualifying context, original step numbers and citations. Questions use a neutral compositional grammar to keep generated product advice out of the response. Transport outages remain service errors, distinct from searched coverage gaps.
6. Session revisions reject stale concurrent writes. Langfuse records interpretation, selection and contract failures. The application currently retains its single-request admission limit; the revision guard does not increase model throughput.

## Conversation and access boundaries

The LLM chooses the passages and conversational strategy. Factual wording remains the article’s exact text. It can answer precise
questions, interpret natural progress reports, ask clarifying questions, and
resume a goal after a prerequisite such as credential recovery. User reports
remain unverified reports: they do not establish permissions, eligibility,
submission, or approval. Support facts must come from the approved articles.

The server retains the role, course mapping, and source authority. All five roles
have explicit access to the approved general learner articles; management and
role-specific procedures retain their independent grants. An Instructor claiming
to be an AO in chat cannot retrieve AO-only copying procedures. Profile selection
is simulated identity, not production authentication.

The current corpus has coverage gaps for card-PIN reset/unblock rules, automatic denial based on missing prerequisite documents, and remediation when credential-recovery navigation itself fails. The active path lets the model assess coverage against retrieved evidence; older keyword routers remain only for historical diagnostics.

Conversation history is bounded. Active user facts and superseded facts are distinct, so a correction can withdraw an earlier completion without deleting unrelated progress. Screenshot observations are untrusted observations, not authority. The active entry is `rag.answer_question` → `flexible_support.answer`. The active model transport uses `compact_interpretation`, `compact_relevance`, and `compact_reply`: quote IDs establish user provenance; a normalized query is used only for retrieval ranking; a bounded model selection filters already authorized retrieved sources for task relevance; and selected source passages pass the existing authority and condition checks. Optional unsupported context is discarded independently. Conversation quality still requires real-model testing; these contracts do not establish semantic correctness. Earlier scripted dialogue fixtures remain outside the maintained guard runner; they are not current-model acceptance evidence.

The planner is fallible. Exact article wording prevents invented factual
additions, but a selected passage can still be irrelevant or unhelpful. Valid
citations and HTTP success do not establish conversational quality. Real VM synthetic
conversation review is recorded separately from offline regression tests in
`docs/long-dialogue-validation.json`; the previous compact pass is in `docs/compact-dialogue-validation.json`; earlier planner results are recorded in `docs/planner-redesign-validation.json`, and the prior redesign is recorded in
`docs/conversation-redesign-validation.json` and the earlier evaluation remains in
`docs/llm-behavior-validation.json`. Tests cover the selected nineteen articles,
not the full knowledge base or real-user accuracy.

## Target knowledge-base size

The user’s intended end state is **200–300 approved articles**. The current
nineteen-article demo does not establish readiness at that size.

Design and evaluation should account for:

- A bounded, relevant set of permitted passages per turn, with section conditions
  and complete procedural context preserved. Model context should not grow by
  including the entire corpus or an unbounded article catalog.
- Reviewed article metadata for identity, explicit role grants, course/system
  scope, provenance and version. Missing access metadata must still deny access.
  Adding approved articles should become an ingestion/data operation rather than
  requiring a new conversational branch for each article.
- Retrieval tests with overlapping topics, similar button names, irrelevant
  distractors, conflicting scopes, missing coverage and restricted articles.
  Measure retrieval quality separately from response usefulness and latency.
- Repeatable validation, indexing, updates and retirement of approved articles,
  with evidence that withdrawn or newly restricted content cannot remain in use.

This is a future design and acceptance target, not a completed scale test or a
bulk-ingestion approval. The next model comparison should keep its controlled
baseline, while later acceptance must also demonstrate behavior with the larger
approved collection. More articles alone will not resolve the observed planning
and follow-up failures.

## Project structure

- `backend/` — FastAPI chatbot, role policy, retrieval, grounding, and ingestion.
- `frontend/` — Browser-based demo interface.
- `knowledge/curated/` — Runtime JSON dataset and taxonomy.
- `hackathon-dataset/` — Plain-text dataset prepared for hackathon upload.
- `hackathon-dataset.zip` — Zip archive containing the nine upload-ready `.txt` articles.
- `tests/` — Offline routing, grounding, session, and dataset checks.
- `scripts/` — Guarded deployment and verification tools for the isolated demo.

## Validation

Run the offline checks from the repository root:

```bash
python tests/run_contracts.py
node --test tests/test_intake_conversation.js tests/test_guided_replies.js tests/test_reply_formatting.js
python backend/ingest.py --manifest knowledge/curated/manifest.json --validate-only
```

The maintained runner uses an explicit list of current server guard modules: compact
interpretation/selection, task memory, provenance, source conditions, registry,
sessions, configuration and release isolation. It records the exact modules,
test IDs and excluded legacy/mixed fixture modules in its JSON report. Broad
unittest discovery is not the current acceptance entry point. Earlier model-stage
mocks and scripted dialogue outcomes are excluded rather than reported as chatbot
quality. Shared fixtures live in `tests/support.py`.

Conversation acceptance now relies on serialized conversations against the real
application and current VM model, with independent transcript/source review.
Deployment health and HTTP success do not count as useful answers. The latest
sanitized evaluation record is `docs/long-dialogue-validation.json`; private
HTML reports preserve exact synthetic conversations and failed candidates.

The current path also checks clause-scoped context provenance, answered clarification
purposes, task retention under memory pressure, and candidate backfill before the
four-source cap. Source-owned section conditions accompany evidence; the reviewed
unlock wait branches enforce explicit elapsed-time reports. Other semantic conditions
still require model judgment. Conditional instructions retain their wording without
claiming the user has completed a future prerequisite. Answers may include a selected-
source outcome follow-up; acknowledgements cannot claim resolution without an explicit
success report. The offline examples are simulations, not live behavior measurements.

Adding or changing reviewed section metadata changes the registry release hash.
Refresh the isolated demo index through the existing deployment workflow before
activating this build, even when factual article text and embedding vectors are unchanged.


Real PostgreSQL/pgvector contracts run separately in a disposable local Docker container:

```bash
python tests/integration/database_contracts.py --run
```

This runner uses synthetic vectors, an isolated database and a random loopback port;
it removes its own container afterward. It checks ingestion, unchanged-vector reuse,
SQL permissions, session revisions and query bounds at 300 synthetic articles.
It never connects to the application VMs or the real LLM. Results are written to
`output/test-suite-refresh/database-results.json`.

Neither offline suite measures live model usefulness, semantic recall or response
latency. Those require real API conversations and separate transcript review on the live
application; the model connection is restored. A safe rejection passing a boundary test
must not be counted as a useful-conversation success.

## Growing the knowledge base

The guided flow has offline checks and bounded live conversation coverage. The next review batch should select five
to ten articles spanning similar symptoms with different causes, follow-up/failure/
escalation paths, and role contrasts. Titles and an index are useful for selecting
that batch without importing the complete raw corpus. Every candidate needs the
approved role, course, area, and provenance metadata; an article with missing role
metadata is denied. The assistant must not invent course facts, and sensitive full
knowledge-base material must not be committed.

Five source articles and the additional Moodle app article from the user-provided Confluence export have been reviewed and added to the local curated manifest. Their references, audience decisions, routing rules, and the scoped annual-cyber wording audit are recorded in [the batch review](docs/knowledge-base-next-batch.json). The four follow-up sources in [the competition batch](docs/retrieval-competition-next-batch.json) are also approved, curated and indexed. The declined disabled-account reactivation article is excluded. Only selected sources were adapted; the full export was not extracted or imported.

The versioned `knowledge/curated/manifest.json` is the reviewed article registry. Each entry binds its file hash, explicit role grants, service/course scope, applicability and bucket. Adding a reviewed source requires adding its JSON and registry entry, updating the release ID, and running validation; it does not require an article-specific Python registry edit. New buckets also require the matching reviewed taxonomy. Packaging includes only registry-named article files. Public redistribution status and provenance still require review for each addition.

Ingestion fingerprints exact embedding inputs and the configured model tag. Unchanged vectors are reused; changed vectors are prepared before a short atomic database publication. `ingest.py --check-only` checks release, canonical content, metadata and embedding consistency without model calls. Existing indexes without these fingerprints need one explicit migration. A model tag is not an immutable model digest; a replacement under the same tag must be treated as an index migration.

Code deployment now checks the index before interrupting the running demo. `--reindex` explicitly updates articles; code-only releases do not automatically re-embed them. `--allow-model-unavailable` permits application activation with a verified index during an inference outage and records conversation verification as blocked. `/api/ready` reports application readiness; `/api/health` also checks required model names. Neither endpoint claims successful inference. Live conversation verification remains a separate deployment check.

The demo requires Python 3.12 for the application environment. Dependencies are pinned in `backend/requirements.lock`.

## Isolation

The hackathon demo uses its own containers, database, vector data, sessions, configuration, and tracing project. Runtime credentials are not stored in this repository. The separate operational chatbot and its knowledge base are outside this project's deployment scope.

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
