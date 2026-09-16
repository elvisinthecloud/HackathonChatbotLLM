# Test recovery report

Source: Codex session records dated 2026-09-16 for `/Volumes/USB_64_A/HackathonChatbot`; no Atlas, network, deployment, or credential access was used.

## Recovered exactly

- `tests/test_grounding.py` — complete source recovered from captured test output, including the final mocked Instructor grounding test and generic URL mutation checks.
- `tests/test_sessions.py` — complete source recovered from captured test output and the later citation-bound edit.

## Not recovered

- `tests/test_backend.py` — only a prefix and a separate suffix were present in session captures; the middle is missing. It is intentionally omitted.
- `tests/test_policy.py` — no complete source or sufficient patch sequence was found. It is intentionally omitted.

No credentials, raw chat transcripts, caches, compiled artifacts, or unrelated files were included.
