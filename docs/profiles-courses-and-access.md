# Profiles, tasks, and article access

The demo keeps vector RAG with explicit server-side permissions. It does not use GraphRAG. Static server records in `backend/demo_policy.py` define seeded identities and confirmed course mappings. The browser selects a profile ID; it cannot supply role claims or chat history. This is simulated identity, not production authentication: any attendee can intentionally choose any seeded role.

## Independent grants

| Display role | Server role | Permitted article | Required task/system |
| --- | --- | --- | --- |
| Student | Student | MCELE-LAUNCH-001 | Course content in MCeLE, with exact error evidence |
| Instructor | Adjunct Faculty | MOODLE-COPY-002 | Course management in Moodle; permission guidance only |
| Academics Officer (AO) | Academics Officer | MOODLE-COPY-001 | Course management in Moodle; copying steps/tutorial/training reminder |
| Academics Officer (AO) | Academics Officer | MOODLE-COPY-003 | Course management in Moodle; slow, stuck, timed-out, or failed copy troubleshooting |
| Training Manager | Training Manager | MCELE-ECDEP-001 | Enrollment in MCeLE; 5500 or 6800, or general guidance explicitly scoped to those seminars |
| Training Manager | Training Manager | MCELE-ENROLLMENT-REPORT-001 | Enrollment reporting in MCeLE; verify a Marine's enrollment status |
| Student | Student | MCELE-RRC-001 | Reserve Retirement Credit guidance in MCeLE |
| Regional Director | Regional Director | None | Presentation placeholder |

There is no inheritance. A profile's course/system associations are context hints, not additional access grants. Course scope is relevance metadata, separate from role access. General MCeLE launch guidance can apply to CYBERM0000 or CDETBAIC01 when the exact error is evidenced. Training Manager guidance is not extended to CSC/EWS enrollment merely because enrollment is also on MCeLE.

Both article-candidate search and all chunk/follow-up searches require request-local server access, the curated dataset marker, explicit role metadata, the task's system, and an allowlisted article ID. Missing access context raises before database access. Missing article role metadata cannot satisfy the query. No separate article-download/preview API exists; citation previews come only from the same filtered results. No retrieved article results are cached across profiles.

## A course can span systems

User correction accepted on 2026-09-14: course alone does not identify which system a support question concerns. Earlier documents describing 5500 as MCeLE-delivered are superseded by this task-specific mapping.

| Code/name | Course content | Enrollment | Discovery portal |
| --- | --- | --- | --- |
| CYBERM0000 | MCeLE | Not confirmed separately | MCeLE |
| 5500 — Sergeants School Seminar Program | Moodle | MCeLE | MCeLE |
| 6800 — SNCO Leadership School Seminar | Not confirmed | MCeLE | MCeLE |
| CSC — Command and Staff | Moodle | MCeLE | MCeLE |
| EWS | Moodle | MCeLE | MCeLE |
| CDETBAIC01 — Basic AI Course | MCeLE | MCeLE | MCeLE |

The registry uses only user-supplied mappings. EWS is displayed by code rather than inventing a corrected full title. The course field accepts a known code, name, alias, or unrecognized text. Recognized mentions in messages/screenshots also provide context. Unknown course text does not create a new registry record or establish a platform. The user may clarify a missing system for that conversation.

Task categories are enrollment, course content, course management, and course credit. A course-only question asks what the user wants to do. Mapping and task determine the current system; seeing a Moodle course in the MCeLE catalog does not make its content MCeLE-delivered. Explicit course selection takes precedence over inferred previous context; contradictory selected/mentioned courses or system evidence require clarification. Task recognition is a small deterministic set of phrases tailored to the reviewed scenarios; it is not a general intent-classification model. Within course management, stuck-copy language selects the AO troubleshooting article instead of the normal copy procedure. Within enrollment, report or status-verification language selects the Enrollment Report article instead of the ECDEP Recommend/Deny workflow.

## Screenshot behavior

The existing qwen2.5vl:7b model transcribes screenshot text. The existing chat model answers using only the subsequently permission-filtered excerpts. The Student article requires the exact hostname `sts1.auth.ecuf.deas.mil` and `refused to connect`, plus MCeLE course-content context. A vague launch failure, unreadable screenshot, generic refused-to-connect error, enrollment task, or Moodle course content does not unlock the article.

The selected course identifies context; it does not establish the error. Screenshot text and user text are evidence, not instructions granting access. The clearly labelled fixture in `verification/synthetic-sts1.png` is generated with Pillow by `verification/make_screenshot_fixture.py`; it is not a real MCeLE screenshot. Real screenshot verification remains subject to the user supplying their intended screenshot.

## Conversation storage and isolation

Each explicit profile selection creates a fresh server session. Its random token is returned only to the browser; Postgres stores a SHA-256 token hash and an independent internal conversation UUID. Role identity is fixed by the server profile record for that session. Langfuse uses the internal UUID rather than the bearer token. Reloading the page requires selecting a profile again. No browser localStorage/sessionStorage contains transcripts or tokens.

Profile changes clear visible messages, course text, draft input, image attachment, and resolved context. In-flight controls are disabled; asynchronous image reads are discarded if the profile/session changed. Clear creates another fresh session. A course or task change stays in the same transcript but increments the context version, so prior system assumptions, model history, and error evidence do not carry into the new context.

Postgres retains up to 100 completed turns per session, including question, answer, context, trace ID, and extracted screenshot text. Raw screenshots are not stored in the database. Model history is separately bounded to six recent turns/12 messages and 12,000 characters from the current context version. User/vision error evidence can survive beyond that short model window within the same context. Full earlier turns remain available for the future ticket handoff, which has not been implemented.

Sessions expire for API use after 24 hours; records are retained until a separately reviewed demo-data cleanup. At most 500 unexpired sessions are admitted. No automatic deletion touches original or demo transcripts. The API accepts neither browser history nor arbitrary profile/role claims on chat requests. Feedback must belong to the requesting session.

## Deployment and verification

The dedicated Atlas database, volume, network, ports, resource limits, and Langfuse project remain unchanged. Ingestion transactionally indexes exactly four approved articles and retires only the two named synthetic baseline records in demo storage. It creates only `demo_sessions` and `demo_turns` in the identity-checked demo database. The existing public demo tunnel is preserved during routine code updates when it is running, helping preserve its random URL.

Run local tests with the documented Python environment, then use `scripts/deploy.py --apply` under the existing approval. The deployment verifies an Instructor conversation and its trace before declaring success. `scripts/verify_scenarios.py --run --synthetic-screenshot <release>/verification/synthetic-sts1.png` runs bounded sequential role/course/vision checks on Atlas. It prints only verification summaries and trace IDs, never keys or session tokens.

The deployed release still contains the original four approved article bodies. The local expansion contains seven curated article bodies; metadata and editorial notes are not embedded. Redistribution status remains pending for public submission packaging. Ticket destination/fields and final walkthrough remain deferred.
