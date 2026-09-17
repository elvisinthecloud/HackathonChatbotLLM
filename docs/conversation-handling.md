# Conversational turns

The deterministic recognizer in `backend/conversation.py` accepts only complete
messages composed of reviewed greetings, thanks, acknowledgements, and generic
capability questions. Unmatched words cause the whole original message to follow
the existing support pipeline. It does not rewrite the question or use a model.

Examples: `Hello!`, `How are you today?`, `Thanks, I appreciate it.`, and
`Oh okay, thank you! Are you able to help me with other things?` receive short fixed
replies. `Thanks, but I still cannot launch CYBERM0000` remains a support request.
Messages with screenshots always follow support processing.

The server returns `response_kind: conversation` with zero retrieved chunks,
empty sources, no clarification, and a trace marked `retrieval_skipped: true`.
Other responses are `support`. The browser uses this field to retain the pending
intake category through social replies, consuming it on the first support reply
(including a clarification). A failed request also retains the category.

The existing session save records every turn. A server-generated `_response_kind`
marker is stored only in that turn's existing context JSON, never in the session
context. Social turns are excluded before bounding support history and evidence.
Unmarked historical turns keep their prior behavior. No schema migration is needed.

An unchanged course selection preserves even unresolved support context. A changed
selection is resolved without social text and advances the context version, so old
course history and error evidence are unavailable to subsequent support requests.
Social turns still count toward the existing 100-turn session limit.

## Validation and release boundary

Run `python -m unittest discover -s tests -v` with backend dependencies installed,
and `node tests/test_intake_conversation.js` for the intake lifecycle checks. These
are offline tests; model, retrieval, tracing, and database interactions are mocked
where required. They cannot establish live embedding ranking, model quality, or
deployment parity. Before release, run the existing serial demo checks and manually
verify the conversational sequences, CSC, and EPME on the isolated demo after
deployment is separately authorized. Check traces for no retrieval/model spans on
social turns and normal permission filtering on subsequent support turns.

Focused rehearsal after an authorized deployment:

1. As Student, select Courseware Issue, then send `Hello!`, `How are you today?`,
   and `Thanks, I appreciate it.` Each should be short and source-free.
2. Send `I cannot launch my CYBERM0000 course.` Expect the exact-error/screenshot
   clarification and no search. Then send `The error says sts1.auth.ecuf.deas.mil
   refused to connect.` Expect only MCELE-LAUNCH-001 and its approved guidance.
3. In a fresh AO session, obtain the stuck-copy answer, then send `Oh okay, thank
   you! Are you able to help me with other things?` Expect `Yes. What would you
   like help with?` and no search. A genuine follow-up must still use support context.
4. Change course during a greeting, then report a vague launch failure. Confirm
   old exact-error evidence is not reused. Repeat Instructor/Student restricted
   requests and the existing approved scenario checks before calling this live-ready.

No model, retrieval-ranking, role policy, grounding, dataset, or schema changes are
part of this patch. The release allowlist includes the new helper to avoid a missing
module in a future approved release. Nothing is deployed by these source changes.

## Deliberate limitations and fallback

Live validation confirmed the conversational bypass and delayed retrieval. It also
found two limitations outside this patch: a Student follow-up can contain advice
absent from its retrieved article (the current grounding check does not reject all
unsupported prose), and an AO follow-up naming "Content Management" can be
misclassified as a course-content task. A context-only policy follow-up retrieved
the expected copy article. Successful routing does not certify full answer grounding.

This is an English phrase allowlist, not general intent recognition. Unrecognized
social wording can still receive the existing support clarification. Ambiguous
short replies such as `yes`, `no`, or `it still fails` are deliberately left to
support processing. No general topic-reset behavior or follow-up heuristic changes
are included.

The pre-existing same-context topic-change issue remains: after a Training Manager
asks about an Enrollment Report, retained report evidence can affect a subsequent
ECDEP question for the same course. Use separate conversations for independent
presentation scenarios. Do not infer that a generic capability response clears the
previous support issue.

If validation reveals a regression, revert this patch as a unit and keep the known
working release. Present direct issue reports in separate conversations. No data
rollback is required; older code ignores the per-turn JSON marker.
