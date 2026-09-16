# Answer grounding correction — 2026-09-16

Status: deployed as `150982c95159b944`; final live checks are in progress. Before editing, the USB allowlist hash matched the recorded deployed release `c0e172cd39238e51` exactly. Deployment uses only the approved isolated demo resources.

Release: `150982c95159b944` (includes the optional Tailscale deployment transport). Validation passed: 55 offline tests (including a mocked final Instructor chat response and exact URL mutations), JavaScript syntax, the four-article manifest, pinned dependency compatibility, and the 34-file deployment plan with rendered Compose isolation/resource checks. The serial live verifier was expanded to check Instructor grounding and the complete AO procedure.

## Problem and correction

The handoff reported an Instructor answer with an invented tutorial URL and AO training advice absent from its permitted source. Automatic paragraph citations made that material appear supported.

The prompt now explicitly forbids URLs, tutorial/training claims, and steps absent from current permitted excerpts. After generation, Moodle copying answers use the complete permitted article content verbatim, with citations attached to those copied excerpts. Instructor content therefore remains permission guidance; AO content preserves all eight steps, the tutorial URL, and the MClearn reminder/link. Retrieval permissions remain the authority; no second source lookup or role inheritance is introduced. Existing model calls and traces remain in place.

For other articles, generated HTTP/HTTPS destinations are compared exactly against those in permitted chunk content, including query strings and fragments. An unsupported link replaces the entire generated answer with cited permitted excerpts, removing associated invented text rather than merely deleting its URL. Parsing follows the frontend's Markdown and bare-URL forms. This is a conservative fallback: punctuation attached to a bare URL may also cause fallback. Generated paragraphs no longer receive automatic citations; existing references are bounded to available sources.

This does not claim general semantic verification of all generated prose for Student and Training Manager answers. Those answers still use source-only prompting plus link validation. The copying scenarios use deterministic excerpts specifically to enforce their content boundary and preserve the approved procedure.

## Access and remaining deployment checks

The documented native-filesystem Python 3.12 environment was recreated at `/private/tmp/mcele-demo-venv`, using `backend/requirements.lock`. Dependencies and caches are not stored on the USB.

Tailscale resolves Atlas to `100.122.223.11`. The user added an SSH rule for this account, and authorized Tailscale access now succeeds. `scripts/deploy.py --transport tailscale` uses Tailscale authentication and host verification; ordinary SSH remains the default for existing users. No credentials were added to project files.

Once access is available, use the existing guarded deployment workflow within the already-approved isolated resources. Recheck the live release and original health before applying. Run the expanded serial verifier (now explicitly comparing Instructor and AO content), verify dedicated Langfuse traces, compare both roles in the public UI, verify profile switching, and check original health and 315 chunks. Until then, retain the prior release and live-validation records as historical evidence, not evidence for this correction.

The user confirmed that GitHub push must wait until the project is completely finished. No repository was initialized and nothing was pushed. Real screenshot verification, ticket destination/fields, and content redistribution review remain pending.
