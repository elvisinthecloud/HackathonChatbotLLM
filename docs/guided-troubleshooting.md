> Current implementation: the isolated demo uses LLM-selected, exact article
> passages and bounded clarification questions in `backend/flexible_support.py`. The fixed-step checkpoints below are
> historical. See `README.md` for the current pipeline and
> `conversation-redesign-validation.json` for the understanding-first redesign
> evaluation and limitations.

# Guided troubleshooting

The demo supports a bounded, one-question/one-step troubleshooting conversation.
It is designed for reviewed support paths where the next useful action depends on
an answer such as “yes”, “no”, an exact error, or a changed symptom. The server
owns the state so that the browser cannot grant itself a role, source, course, or
previous error context.

## How a turn is handled

For each support turn, the server loads the session created for the selected demo
profile and resolves the current course, task, and system. It then checks the active
troubleshooting topic and evidence. A changed error or a new topic resets the
guided path and removes stale evidence from the current model context. The complete
transcript remains available in the session record for later handoff work, but old
state does not answer a new problem implicitly.

When a guided path needs input, the response records one pending question. The
browser can show the question and, when supplied, optional `suggested_replies`
quick reply buttons. A typed answer works the same way. The server consumes a
yes/no reply only when it matches the pending question; an unprompted “yes” or “no”
continues through normal support clarification. The next response contains one
source-backed step or asks the next bounded question.

Quick replies also require the current response to show the matching server
question. Yes/No is offered only for a binary question, and Done/I'm stuck only
for a step-completion prompt. The error-change button requires a known reported
error. Greetings and thanks do not inherit binary choices from a previous question.
Open error, course and diagnostic questions use typed replies. The obsolete dynamic
clarification-option response and manual retrieval-bucket selector have been removed;
ambiguous retrieval still asks for context in text. The opening issue-category
buttons remain available.

Source-backed rendering happens after access resolution. Role, task, course scope,
system area, article allowlist, and required evidence are checked before every
guided step and every source reference. Only the permitted article excerpt and its
approved links can supply troubleshooting facts. Missing role metadata denies the
article. The renderer does not fill gaps with course facts, links, or procedures
from memory.

This preserves the existing architecture:

1. The selected profile resolves to a server-owned simulated identity.
2. Session context resolves course/task/system, including courses that span MCeLE
   discovery, enrollment, and Moodle content.
3. Access policy filters candidate articles before semantic retrieval or model
   context.
4. The guided state machine decides whether to reset, ask one question, or render
   the next step.
5. One joint call to the existing Qwen chat model interprets intent, explicit
   current-user progress and an optional permitted source-unit selection. The
   server validates the closed schema and evidence, re-runs policy, then applies
   progress only to a matching authorized procedure. Failed interpretation asks
   for clarification without marking completion. See the boundary below.
6. The turn and context version are retained in the isolated demo session.

The nineteen selected articles form the curated dataset. Guided troubleshooting does
not crawl directories, import the raw corpus, or create new role access. The
existing explicit manifest, policy, taxonomy, clarification buckets, and release
allowlist continue to govern ingestion.

## What is verified

`tests/test_guided_conversation.py` covers the server state transitions, including
one-step progression, pending yes/no handling, changed-error/topic reset, and
permission filtering on follow-up references. `tests/test_guided_replies.js` covers
optional quick-reply rendering, resets, and use of the existing send-message path
with a fake browser DOM. `tests/test_guided_verification.py` checks the future live
verifier's bounded traversal and trace access checks with mocks. Run the focused checks
with:

```bash
python -m unittest discover -s tests -p 'test_guided*.py' -v
node --test tests/test_guided_replies.js
```

The tests are offline checks. They use local fixtures and mocks where needed; they
do not prove live Ollama retrieval ranking, passage selection, database health,
network behavior, or deployment parity. A live verification run needs the reviewed
isolated demo and the existing deployment checks. This private development branch
differs from the public `main` recovery baseline, and no deployment is implied by this
guide.

## Supported paths and limits

Procedures advance only after the user reports completion. A failed step asks what
happened; a bare yes cannot answer that diagnostic question. Explanations preserve
the current step or visibility question. Completing a procedure prompts an outcome
check, followed by the approved escalation if it still fails. Greetings and thanks
preserve progress.

CSC checks visibility in MCeLE before Moodle and confirms the All filter before
choosing Region-first escalation. General EPME questions ask which course; an
explicit request to compare all courses returns the approved comparison. ECDEP
asks which seminar when its course is missing. Instructor copying guidance remains
limited to permission instructions.

The model interprets paraphrased intents and reported progress. Server patterns
still protect explicit conflicts, negative/hypothetical claims, exact errors and
reviewed business rules. The guide follows one selected article at a time;
a new cause or ambiguous wording may need clarification. Source copying protects
facts and links but cannot prove that the model selected the most relevant passage.
It also limits conversational paraphrasing. Adding articles requires reviewing
routing and these paths, then checking live retrieval when the VM is available.

## Reviewed login and course-access batch

Six selected Confluence articles were adapted with original page IDs and source paths:
MCeLE login, CAC login problems, credential recovery, enrolled-course launch,
Moodle browser access, and Moodle app access. Each explicitly grants all five seeded
roles, including Regional Director. Existing course-management and enrollment grants
remain independent; selecting an AO or instructor profile does not itself make a
learner's access problem a management task.

`backend/access_support.py` resolves the reviewed support topic and branch before
retrieval. The source renderer retains Markdown section labels, so CAC login loops,
password reset, a missing recovery email, launch pop-ups, active sessions, and blank
pages can follow separate contiguous procedures. A completed-step report advances
only the reported actions; a missing recovery email switches to that branch rather
than repeating the reset request. The current source question can explain a permitted
step and return to the procedure without marking it complete.

An unspecified Moodle login request defaults to browser access through MCeLE's
**Instructor-Led Courses** left navigation. Phone wording alone asks app versus
browser. Server context stores `moodle_access_method`, `entry_point`, `failure_stage`
and `support_branch` independently from the six-exchange/12,000-character history.
“I mean the app” switches source and clears browser step progress. Later brief
follow-ups retain the app choice, including after the original message leaves the
recent-history window. Explicit browser, course and topic changes reset the old path.

A Launch click in MCeLE does not establish the course-content platform. Known course
mappings take priority. An unknown launch request first asks which course; an
unconfirmed destination asks self-paced MCeLE versus Instructor-Led Moodle. A failed
MCeLE-to-Moodle handoff uses the left navigation directly. QR-code and locked-out app
reports use their own source sections. Missing Moodle tiles, broken activities and
created-course problems use **Student Support Help Desk, option 3 for Moodle support**.
The previously reviewed CSC-specific Region-first path remains separately scoped.

`tests/test_access_support.py` covers these source-based offline conversations,
including all-role source hydration, method retention beyond the history window,
negative completion reports, topic/course switches and protected management sources.
The new files are included in all ingestion and release allowlists. The access
batch and four later approved articles were indexed in the isolated VM demo on
2026-10-02. The earlier nine-file upload archive is unchanged.

## Further knowledge-base growth

The current flow passes offline checks. Select a small review batch of five to ten articles.
Prefer articles that cover similar symptoms with different causes, explicit
follow-up/failure/escalation paths, and contrasts between roles. Use titles and an
index to choose candidates without copying the complete raw corpus. Each selected
record needs approved role, course, area, and provenance metadata. Missing roles
remain denied, and unsupported course facts must remain unanswered or clarified.

The current ingestion path is explicit rather than automatic: configuration,
article files, policy, buckets, taxonomy, manifest, and release allowlist all need
review when a selected article is added. Do not commit the sensitive full knowledge
base. Preserve provenance and review redistribution status for each approved
addition.

## Retrieval competition evaluation

`docs/retrieval-evaluation-cases.json` contains synthetic user reports and expected
source/clarification/denial behavior derived from the reviewed decisions. The default
`scripts/evaluate_retrieval.py` run audits the pure-Python context/access router,
without fabricating successful retrieval. It does not exercise procedure progress
or model wording. A route passes when its action matches and its candidate set
contains the expected source; it does not mean the final source was ranked correctly.

```bash
python scripts/evaluate_retrieval.py --output docs/retrieval-evaluation-plan.json
python -m unittest discover -s tests -p 'test_retrieval_evaluation.py' -v
```

The historical 2026-09-30 offline audit covered 43 scenarios and 46 turns. Forty-two routing expectations
match; four natural paraphrases trigger clarification despite describing a reviewed
support path. These are routing gaps, not measured vector-search mistakes. Thirty-five source turns have
only one production route candidate, so these routing checks do not establish that
vector search can distinguish competing sources. Existing score-margin ambiguity
logic compares bucket membership; multiple articles sharing one bucket can still
be treated as one route. A copied, accurately cited answer can come from an
inapplicable article. Source correctness and response grounding need separate checks.

The runner can separately rank the six-source access subset and all selected
articles with the unchanged `nomic-embed-text` model. `--embed-live` is guarded to the
approved host with its configured private runtime environment and performs bounded
sequential embedding requests only. It uses ingestion's chunking and dedicated AO
retrieval text, then ranks each article by its strongest chunk. It does not ingest,
write the database, deploy, call the chat model, or run the production API. Do not
run it while the VM is unavailable. A vector cache can be supplied with `--vectors`;
the cache must match selected-source hashes, model identity and vector dimensions,
but its claimed origin is not independently verified. Keep caches outside tracked
source. No model or vector ranking was run for the saved offline report.

The ranking diagnostic deliberately replaces intent-based article narrowing with
explicit role/system/course/evidence masks so competition is visible. It never
supplies chatbot answers or changes production access. Queries use user reports
since a context change, not assistant output. This exhaustive cosine ranking is
separate from the actual pgvector/API path and needs comparison with live retrieval
traces before claiming production accuracy. It reports top-one correctness,
top-three coverage, wrong top results and score gaps. Cases expecting clarification
are recorded separately, not counted as successful forced article choices. Similarity
scores and the existing 0.05 margin are not calibrated probabilities or proof of
correctness. Interpret changes on the same query set, with role/course masks held
consistent, and review actual mistakes before tuning thresholds or adding reranking.

The user reviewed four further overlapping sources in
`docs/retrieval-competition-next-batch.json` and declined the disabled-account
reactivation source. The four approved sources are curated and indexed.
`backend/account_course_support.py` handles their task distinctions and stores the
CAC-association parent goal in server context during credential recovery.
The new deterministic route audit matches 53 of 53 fixed expectations. The live
embedding diagnostic ranks the expected article first in 38 of 48 source turns
and includes it in the top three for all 48. On the same 33 access queries, the
six-source baseline and nineteen-source pool both rank the expected article first
24 times. These are embedding diagnostics with a broad permitted pool, not actual
answer accuracy: production intent narrowing often permits only one article.

## Live synthetic conversation findings — 2026-10-02

Three agents ran new, isolated sessions with unfamiliar wording, precise requests,
and role/context changes. The baseline had 13 conversations and 47 HTTP 200 chat
turns; eight targeted replays added 49 turns, and two final checks added six.
All 47 baseline traces were inspected. Two contained Qwen passage-selection calls;
most replies followed server guidance and approved source excerpts. These checks
do not evaluate unrestricted LLM interpretation, general user accuracy, or capacity.

The live checks exposed context loss after waiting, CAC recovery completion being
missed, staff-role enrollment routing persisting after a correction, and request
form progress being ignored. Deployed fixes and targeted replays cover those
transitions, including automatic versus manual unlock and typed PME course codes.
Moodle access-method changes and role-specific copying guidance held their scope.

Natural completion reports such as "I found it" or "Done, I did that" can still
repeat catalog steps. A request to retake a completed course can return listing
navigation. Negated CAC/PIN guesses can need repeated clarification. Manual review
marked these replays partial even when an agent reported success based on source
selection. See `docs/synthetic-testing-summary.json` for sanitized totals and limits.
Complete transcripts, trace evidence and the HTML report stay outside Git.


## Model interpretation boundary

The October 2 local implementation in `backend/intent_interpreter.py` and
`backend/rag.py` makes one joint Qwen call for each non-social support turn. Pure
social replies continue to skip model and retrieval calls. It preserves
`qwen3:30b-a3b-instruct-2507-q4_K_M`, `nomic-embed-text`, and `qwen2.5vl:7b`.
No model settings, source grants, corpus, infrastructure or resource limits change.

Before interpretation, the server may read one already-permitted article using
the same dataset, role, system and article metadata filters as retrieval. Complete
curated source units are offered only after those checks; ambiguous or denied
routes offer no source text. At most 48 units and the existing context-character
limit are offered. The prompt includes the current message (up to 4,000 characters),
screenshot evidence (up to 2,000 characters), bounded server context, the pending
question and current unit. It does not send a second model history window or profile
credentials. Output is limited to 700 tokens with a 45-second request timeout and
no automatic retry. Subsequent support retrieval still uses the existing embedding
and filtered pgvector path; there is no second passage-selection call.

The JSON schema accepts only an enumerated task, a focus selected from server-offered
verbatim current-user spans, an enumerated access method, a new-topic flag, explicit progress reports and
an optional offered answer-unit ID. It cannot return roles, grants, URLs, support
prose, article IDs or arbitrary context fields. The model can interpret misspellings
or discard a superseded guess in favor of the user's stated correction. The server
translates the chosen task into existing policy routing, independently preserves
raw course and screenshot contradictions, and rechecks grants and source scope.
Explicit app/browser wording is required to change method; phone alone cannot grant
the app path. Generic lockout cannot establish a temporary MCeLE account lock.
An unknown course type requires clarification before re-enrollment advice.

Completion must cite affirmative current-user evidence for an offered step or the
pending `current` step. The validator checks the containing clause so quoting only
“found it” from “I haven't found it” cannot confirm completion. Conditional,
negative, future and hypothetical reports are rejected. Reaching a later action
confirms preceding navigation only; reaching Request does not confirm clicking it.
Reports are matched to the source, branch, course and method, and prior-procedure
reports are dropped on context resets. Bare Done/Yes cannot resolve the whole goal
while only a step is pending. A contradictory success/failure report cannot resolve
it either. CAC credential recovery retains the association parent goal.

Malformed JSON, extra keys, unknown intents, model timeouts and source-preview
errors produce a server clarification without completion changes. Component
validation separately discards unoffered IDs, unsafe progress and unsupported
method choices while preserving a valid intent. Invalid focus is replaced by the
original message, never model prose; only case and whitespace normalization may
locate a quoted span. The schema offers only affirmative evidence for completion
and requires empty progress for questions with no reported actions. A failed turn retains an applicable pending step so a later
explicit completion can be retried. The interpreter and its source-unit data are
not persisted in session context; only server-owned state is saved. Langfuse spans
`interpret_support_turn` and `interpret_intent_progress` record validated choices,
offered IDs, fatal rejection reasons and independent `component_rejections`, never exception text or network
configuration. Reset-discarded progress is recorded as `context_reset`.

`tests/test_intent_interpreter.py` exercises the real validator and coordinator
with mocked model transport and approved local article fixtures. It covers natural
completion, mixed navigation, typo routing, corrections, re-enrollment scope,
malformed/timeouts, method retention/switches, CAC recovery/resume, role injection,
selected-course/screenshot conflicts and reset isolation. Existing regression
fixtures explicitly stub interpretation so they remain offline and separately
exercise the pre-existing policy and source guides. The runtime module is included
in both Docker and release allowlists (56 release files).

These checks establish the software boundary, not actual Qwen interpretation
accuracy. The historical live findings above describe the previous release.
Fresh serialized live checks must inspect each answer and interpretation trace,
including rejection frequency, latency and whether the model chooses the useful
next action. Conservative evidence guards may ask for rephrasing; a valid allowed
unit can still be semantically unhelpful. No unrestricted generated advice is used.


### First live interpretation round and contract revision

The first deployed interpreter completed 32 serialized synthetic turns with 32
actual Qwen generations. Twenty-two interpretations were accepted and ten were
rejected; all source/access checks remained consistent. These are partial results:
whole-turn rejection discarded useful intents when Qwen paraphrased its focus or
attached spurious progress to a question. A source-unit guess also preempted an
actual navigation report. The private transcripts and traces remain outside Git.

The local follow-up constrains focus and progress evidence to offered user spans,
adds examples of questions versus reports, and validates components independently.
Validated progress precedes source explanation; initial navigation requests begin
at the procedure entry even if the model selects a later step. Reported clicks
on an identified Select/Click step count as completion; seeing a control does not.
Only the reviewed browser/request-form navigation paths infer preceding navigation
from such a report. A restart never implies cache clearing. The existing approved
form submission/approval limitation runs before generic progression. Generic
uncertainty has no course-task quick replies. Current-user corrections do not
inherit a synthetic staff-enrollment prefix, and explicitly negated course codes
retain the reviewed course-evidence rule.

The next live run must recheck usefulness as well as schema acceptance. These
changes do not establish general interpretation accuracy or expand any source grant.


### Method and progress evidence tightening

The second live round made 34 Qwen calls with no fatal interpretation rejection
and no source/access inconsistency. It still exposed incorrect method guesses:
28 responses chose `unspecified_mobile`, including messages with no mobile-device
evidence. The local revision constrains the method enum to positive method/device
mentions in the current message, always offering `keep` first. App/browser evidence
removes the unspecified-mobile option. The same constraint runs again in validation,
so schema-noncompliant output cannot introduce a Moodle path.

Named progress IDs now require a current-user reference to the corresponding source
control or action. Bold UI labels distinguish, for example, Overview from Request.
Generic Done/found-it reports can only confirm a pending current step; without a
pending step they cannot advance navigation. A named generic report is rebound to
the pending current step, never the model's guessed later step. The schema permits
at most three distinct reports, and validation deduplicates or discards excess
reports. Explicit named navigation can be used at a fresh procedure entry even
when the model marks a new topic; prior pending-current claims remain unusable
across resets. These guard changes preserve the model identities and source grants.

### Final live validation — 2026-10-02

Release `eb5a3023f35c3283` is deployed with the unchanged nineteen-article subset.
The final source passed 199 Python tests and six JavaScript checks. All 56 release
files matched local source, the public demo responded, and original services and
the original 315 chunks remained healthy and unchanged.

The final replay used sixteen fresh synthetic sessions and 37 serialized text API
turns. Every call returned HTTP 200. All 37 dedicated traces were inspected and
showed exactly one existing-Qwen interpretation generation each, with no fatal
interpretation rejection or citation/access inconsistency. One duplicate progress
component was safely dropped. Manual transcript review passed the selected cases;
schema acceptance was not used as the answer-quality grade.

Natural found-it and compound Done reports advance only the pending step. Seeing
Request skips already-reached navigation without confirming the click, and opening
a form never establishes submission or approval. Retake questions clarify course
type when necessary. Explicit CAC/PIN corrections ask for the exact PIN message.
Association survives a recovery detour; Moodle method changes reset old guidance.
Unanswered method questions survive vague Done replies. Initial symptoms,
hypotheticals, negation and contradictory success reports do not confirm progress.
Selected roles, unknown courses and course conflicts retain their server boundaries.

Earlier live revisions failed whole-turn validation, guessed unsupported mobile
methods, or mishandled a symptom and an unanswered method question. Their private
transcripts remain preserved. These observed failures motivated the final guards;
offline fixtures alone had not established actual Qwen behavior.

The replay is prewritten synthetic text, not general model accuracy, full-corpus
retrieval quality, real-user success, screenshot performance, frontend end-to-end
behavior or a capacity test. Conservative evidence checks can require rephrasing,
and explanations remain limited to approved source facts. Sanitized counts and
limitations are in `model-interpretation-validation.json`; full private evidence
and the visual report stay outside Git.

## Flexible article-grounded conversation (local implementation, October 2)

The current production `rag.answer_question` uses `flexible_support.py`. This
supersedes the fixed-step rendering and closed intent contract described above.
The existing Qwen model now chooses the conversational next move and writes the
reply from retrieved approved articles. It can ask a distinguishing question,
explain a detail, interpret an unfamiliar description, or suggest the next action.
It is instructed to use one useful action/question and adapt to reported progress.

The server first resolves immutable role grants, explicit course selection and
conflicts, known course/task mappings, source scope, exact-error requirements and
explicit app/browser evidence. Unknown selected courses, unconfirmed content
platforms and unresolved phone app/browser questions remain clarifications. Bare
Done does not answer those required fields. Profile names/usernames are not sent
to the model. Chat role claims cannot widen the source pool.

A real embedding query searches pgvector separately within the permitted MCeLE
and Moodle pools. The strongest chunk from each article provides the ranking;
the top three distinct articles are hydrated from the startup-verified curated
manifest. At most one still-authorized previous article is retained for continuity.
Retrieval-only ranking text is never presented as source facts. The source budget
is 16,000 characters; whole articles are omitted rather than cut through a condition.
No taxonomy ambiguity gate or closed diagnostic enum chooses the answer route.

The first bounded Qwen call writes exactly one short `answer` or `question` part
(at most 420 characters; questions at most 220) and selects evidence IDs from
source paragraphs or individual numbered lines. Evidence references are not an
action count: multiple spans may establish a factual answer or its conditions.
Answers require evidence; questions must be a single focused question. Numbered
lists are rejected. The server attaches exact source quotes, validates source IDs,
URLs within selected spans, numeric literals and quoted user goals, then adds
citations. A second Qwen call reviews source applicability, unsupported clauses,
reported progress and the useful next step. A coherent navigation step can include
more than one click; factual mentions and conditional alternatives are not steps.
A whole find/details/eligibility/enroll workflow remains a multi-step dump.

A validation or review rejection permits one repair generation with the exact
reason and bounded review findings. The repaired candidate passes the same server
checks and a fresh grounding review. There are normally two generations and at
most four, with no third draft attempt. Transport/unavailable output does not
trigger repair. Repeated rejection returns a clarification and retains prior
memory. Trace metadata records each candidate's decision. Each call has a
60-second transport timeout; draft/repair output is capped at 1,000 tokens and
review at 500. The immutable role and course/method constraints are repeated after
reference data and immediately before the current user turn.

**Limits:** quote membership and a permitted citation do not prove a paraphrase.
The second model review is fallible and may share the drafting model's mistakes.
This is a deliberate change from exact source rendering to generated support,
with additional latency and semantic risk. Live manual review is still required;
offline mocked-model tests do not establish natural-language accuracy.

Memory contains quoted user goals, an optional parent goal, up to eight raw user
reports, the last pending question and previously cited source IDs. Reports are
unverified speech, not completed-step indexes. The model uses them with the last
six support exchanges (12,000 characters) to adapt, preserve prerequisite/parent
goals and avoid repeating failed attempts. New issue/course changes clear active
memory. An explicit Moodle method switch clears old path reports/history while
retaining the quoted goal; using the MCeLE website during a prerequisite does not
switch a remembered Moodle app path. A full independent or prerequisite question
can temporarily defer an unanswered Moodle method question; the unresolved choice
is retained and asked again when Moodle resumes. Methods remain explicit server context. No optional buttons are emitted
by this path; the existing UI removes obsolete prior replies.

The former coordinator remains named `legacy_answer_question` for historical
regression coverage, and is not a production fallback. Legacy tests explicitly
call it. `tests/test_flexible_support.py` exercises the new production entry,
permission-filtered diverse retrieval, natural draft/review boundary, rejected
claims, exact quote/link validation, missing method/platform questions, memory
preservation, nested goals, resets and sanitized transport failure.


The first flexible live revision was rolled back after bounded synthetic checks:
role-claim turns fell back before review, and three sampled accepted answers were
too long or contained unsupported/uncited advice. This demonstrated that the first
exact-quote contract and a single whole-answer review verdict were insufficient.
The local revision now uses short evidence-ID parts, mandatory evidence for support,
explicit immutable-role prompts and per-part review. These changes remain subject
to a fresh live replay; the earlier failed outcomes are not counted as passing.


A second bounded live replay (49 turns) still exposed repeated earlier answers,
multiple-action responses and weak semantic acceptance. The next local revision
uses actual user/assistant history messages with the current user question last,
rather than a single JSON conversation envelope. Server citation markers are
removed from prior assistant text. Initial course confirmation preserves an
unresolved goal; a real course change resets it. Source action lines are separate
evidence spans, the review explicitly inventories proposed actions/unsupported
clauses, and source-span IDs are forbidden in user-facing prose. Question marks
inside UI labels do not become pending questions. Clause-scoped method evidence
separates an MCeLE website prerequisite from a continuing Moodle app goal. Fresh
live verification remains necessary; the prior replay is not a success claim.


The third 49-turn live replay accepted only seven replies, with six policy
clarifications and 36 rejected drafts. The numbered-span cardinality guard was
incorrectly treating source references as actions and has been removed. The local
fourth revision uses one answer/question part, calibrated task-step review and one
bounded repair attempt. It also strengthens role authority placement after the
large reference context. This revision has offline contract checks only until the
next focused live sample; no successful deployment or conversational quality is
claimed here.
