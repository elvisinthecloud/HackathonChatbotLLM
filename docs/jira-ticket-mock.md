# Jira Ticket mock flow

Implemented on `codex/jira-ticket` in a separate Desktop working folder. Main, the CSC article draft, and the hosted demo are unchanged. No real Jira integration, external ticket submission, or live deployment is part of this change.

## User flow

1. Select a demo profile and describe the issue.
2. Choose the issue site using MCeLE or Moodle clarification buttons.
3. Choose EPME4000, EPME5000, EPME3000, 5500, 6800, CYBERM0000, or EWSPREREQ. Course not listed allows an optional free-text course name/code.
4. Continue the conversation, or choose Submit a trouble ticket. An issue typed but not sent can also be used to prepare a ticket.
5. Review the mock Courseware Issues page: username, summary, course, issue type, and description are editable. Username is initially `username.<profile-id>` (for example `username.student`, `username.instructor`, or `username.ao`). Issue type is MCeLE or Moodle.
6. Create mock ticket displays an explicit local-only confirmation. It does not send, persist, or create a Jira ticket. Back to conversation retains the current chat.

The form follows the supplied screenshot's layout while adding the requested username and issue-type fields. It is a view inside the existing application (`#ticket`), avoiding exposure of session tokens or chat details in URLs. It does not attempt to prefill or automate a real external Jira page. A future integration needs the actual portal URL and supported field/API mapping; screenshots alone do not establish that interface.

## Draft generation and isolation

The server resolves the profile from the session token; clients cannot supply a username or override role identity. It selects only user reports and screenshot transcriptions from the current context version that match the selected course and site. Assistant advice is excluded so suggested actions do not become falsely reported attempted actions. A changed course/site with no matching report prompts for a fresh issue.

The existing chat model produces a summary and description with a source-only drafting prompt. The initial and recent reports are bounded to 12,000 characters. User, course, and site fields are set outside the model. The form exposes the original reported details for review and warns that screenshots may be transcribed incorrectly. If model output is invalid or unavailable, the draft falls back to reported text. Ticket generation has separate Langfuse spans/generation metadata and shares the chat concurrency guard. Drafts are not stored and raw image attachments are not transferred.

New course-selector entries do not assert unverified platform mappings. Explicit site selection resolves unknown mappings for the conversation; a conflict with a confirmed task-specific course mapping still denies retrieval. Course relevance and role permissions remain separate.

## Verification

Eleven standalone offline tests cover site/course choices, known-mapping conflicts, context boundaries, absence of assistant-derived facts, unlisted courses, summary fallback, server-owned identity, request validation, and expired sessions. Run:

```sh
python -m unittest discover -s tests -p test_ticket_handoff.py -v
node --check frontend/chat-widget.js
python scripts/deploy.py --plan --transport tailscale
```

Local headless Chrome checks passed for ordered clarification, editable prefill after multiple turns, mock confirmation, back navigation, profile reset, Course not listed, drafting before the first chat response, and mobile overflow. The local preview uses simulated chat/model responses and an in-memory session store; it does not prove live model or Atlas behavior. The old complete test suite remains unavailable because USB recovery did not recover all test files.

No articles or dataset manifests are changed. The release/build allowlists include the new backend module so the branch can be deployed through the existing guarded process after review.


To run the simulated preview locally, install the pinned backend requirements in a Python 3.12 environment and run `python tests/preview_ticket_handoff.py`. Open `http://127.0.0.1:8765`. The preview listens only on localhost. It uses in-memory sessions and reported-text fallback; it never contacts the private services. For browser checks, install Playwright outside the repository or set `PLAYWRIGHT_MODULE` to its module path, then run `node tests/browser_ticket_handoff.cjs` with Chrome installed and the preview running.
