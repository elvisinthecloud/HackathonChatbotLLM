# Recovery report — 2026-09-16

The USB volume `/Volumes/USB_64_A` was no longer mounted when recovery began. This is recovery of the known HackathonChatbot project, not a disk image or recovery of any other files that may have been on the USB.

## Recovered

- All 34 deployed source files from isolated Atlas demo release `150982c95159b944`, byte-for-byte verified against its SHA-256 manifest. This is the working application, curated data, deployment tooling, schema, and synthetic screenshot.
- Four retired synthetic baseline files from isolated demo release `717fbd98c639da62`, checked against that release's manifest.
- Complete Instructor/AO/Student/TM article drafts, role/course policy, source provenance, non-secret configuration template, project instructions, and `.gitignore` from recorded file reads and instructions.
- Two complete test files: `tests/test_grounding.py` and `tests/test_sessions.py`. See `recovery-tests-report.md`.
- Non-secret Atlas inventory and verification reports, the original handoff document, and documentation fragments. Raw conversations, credentials, and production data were not copied.

The new README and current validation/deployment JSON summaries were reconstructed and labeled accordingly. `docs/grounding-fix.md` is an earlier complete snapshot; its pending-verification wording is superseded by the successful Atlas scenario reports. Partial documentation and test source are retained under `recovery/partial-documents/` rather than presented as complete originals.

## Not fully recoverable from available sources

- `verification/make_screenshot_fixture.py`
- `docs/curated-dataset.md`
- `docs/atlas-runtime-verification.json`
- `docs/baseline-validation.json`
- `docs/deployment-review.md`
- `docs/dataset-contract.md`
- `docs/demo-decisions.md`
- `docs/initial-inspection.md`
- `docs/article-discovery.md`
- `tests/test_backend.py`
- `tests/test_policy.py`

These files may be recoverable if the USB becomes readable again. Some document content and backend-test fragments are preserved under `recovery/partial-documents/`. The source manifest covers the working deployed application, so these missing USB-only files do not mean the deployed application source is missing.

Git metadata and the interrupted index were not recovered; no completed local commit or remote upload was verified before failure. No secrets or virtual environments are included. The temporary Python environment had disappeared after the workstation restart.

## Validation and limits

All 34 deployed file checksums match; recovered deployed Python source and both complete recovered tests pass AST parsing. The original 55-test run and live scenario checks passed before USB failure, but the full suite cannot be rerun from this recovery because `test_backend.py` and `test_policy.py` are incomplete/missing. The recovered tests import the missing backend test helper.

Atlas recovery was strictly read-only, limited to the isolated demo release and non-secret reports. The original chatbot, databases, runtime credentials, and running demo were unchanged. GitHub Write access for MajanoJ was subsequently granted. The recovered checkpoint is being uploaded at the user’s request. Unselected-source discovery fragments remain only in the local recovery folder and ZIP, excluded from Git.
