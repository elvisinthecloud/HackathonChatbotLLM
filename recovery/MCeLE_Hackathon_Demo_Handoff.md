# MCeLE Hackathon Demo — AI Agent Handoff

## Exact stopping point

The source-of-truth USB workspace was disconnected before the final grounding fix could be made.

- Local source-of-truth: `/Volumes/USB_64_A/HackathonChatbot`
- Original Atlas chatbot (strictly read-only): `/home/velvux/ChatBotLLM`
- Isolated demo root on Atlas: `/home/velvux/mcele-hackathon-demo`
- SSH target: `velvux@atlas.tail65b4a7.ts.net`
- Current deployed demo release recorded in the prior thread: `c0e172cd39238e51`
- Separate Langfuse project ID: `cmu1njwr40003l808bk5ak05x`
- Public URL recorded in the thread: `https://domain-heater-nelson-tours.trycloudflare.com` (Cloudflare Quick Tunnel; verify because it can change)
- No Git repository had been initialized or pushed at the stopping point.

The hosted demo and original chatbot were healthy after the USB was disconnected. Do not edit the staged Atlas release directly. Reconnect the USB and make all source changes there.

## Current implemented state

The role-aware curated demo is deployed and mostly verified:

- Five server-controlled demo profiles: Student, Instructor/Adjunct Faculty, Academics Officer, Training Manager, and Regional Director placeholder.
- Four curated articles with backend-enforced access before retrieval:
  - `MCELE-LAUNCH-001`: Student; exact `sts1.auth.ecuf.deas.mil refused to connect` evidence; MCeLE course-content context only; excludes Moodle.
  - `MOODLE-COPY-002`: Instructor/Adjunct Faculty; permission guidance only.
  - `MOODLE-COPY-001`: Academics Officer; complete Moodle copy procedure, approved tutorial URL, and MClearn 1100/2100/3100 reminder.
  - `MCELE-ECDEP-001`: Training Manager; MCeLE enrollment Recommend/Deny workflow for 5500 and 6800.
- Server-side Postgres sessions and transcripts, profile isolation, context-version changes, and bounded model history.
- Existing Ollama chat/embedding/vision models and a separate Langfuse demo project.
- Forty-nine offline tests and sequential scenario checks had passed.
- Original chatbot stayed healthy with 315 chunks unchanged.

Course/task mapping is task-specific, not course-only:

- CYBERM0000 content: MCeLE.
- 5500 content: Moodle; enrollment: MCeLE.
- CSC content: Moodle; enrollment: MCeLE.
- EWS content: Moodle; enrollment: MCeLE.
- CDETBAIC01 content and enrollment: MCeLE.
- 6800 enrollment: MCeLE; content platform remains unconfirmed.

## Known unresolved bug

A final manual browser check found that the Instructor answer correctly excluded the AO procedure but fabricated an unsupported tutorial link (`example.com/moodle-copy-tutorial`) and mentioned AO training that is not present in the Instructor article. The model output then received a citation, making unsupported text appear sourced.

No fix was applied because the USB disconnected. The current Atlas release may still produce that bad Instructor response.

## First actions for the new agent

1. Confirm the USB is mounted and open the source folder:

   ```sh
   ls /Volumes
   test -d "/Volumes/USB_64_A/HackathonChatbot" || exit 1
   cd "/Volumes/USB_64_A/HackathonChatbot"
   pwd
   ```

2. Read these files before editing:

   - `AGENTS.md`
   - `README.md`
   - `docs/curated-validation.json`
   - `docs/atlas-deployment-record.json`
   - `docs/profiles-courses-and-access.md`
   - `docs/demo-decisions.md`
   - `docs/deployment-review.md`
   - `backend/prompts.py`
   - `backend/rag.py`
   - `tests/test_sessions.py`
   - `scripts/verify_scenarios.py`

3. Verify the local source corresponds to deployed release `c0e172cd39238e51`. Do not modify `/home/velvux/ChatBotLLM` or edit the deployed release in place.

4. Fix answer grounding in the USB source. At minimum:

   - Add a hard instruction that URLs, tutorial references, training references, and procedural steps may appear only when present in the retrieved article excerpt.
   - Add server-side link validation so every generated URL must be an exact URL found in the permitted retrieved chunks. Strip or reject unsupported links.
   - Reconsider the blanket behavior in `ensure_citations` that appends `[1]` to every uncited paragraph when one source exists; it can make unsupported claims look sourced.
   - Ensure Instructor output contains only the approved permission guidance and no AO procedure, tutorial, MClearn/training reminder, or invented URL.
   - Ensure AO output still preserves the two approved real links and complete procedure.

5. Add tests before deploying:

   - Unsupported generated URL is removed/rejected when absent from the retrieved Instructor source.
   - Unsupported Instructor training/tutorial text is absent.
   - Approved AO tutorial and MClearn URLs remain intact.
   - Citations do not convert unsupported content into apparently sourced content.
   - Existing role spoofing, profile isolation, course changes, Student exact-error gate, 5500 Moodle exclusion, and TM wording checks still pass.

6. Run local checks from the USB project root using the documented Python 3.12 environment:

   ```sh
   PYTHONDONTWRITEBYTECODE=1 /private/tmp/mcele-demo-venv/bin/python -m unittest discover -s tests -q
   node --check frontend/chat-widget.js
   /private/tmp/mcele-demo-venv/bin/python backend/ingest.py --manifest knowledge/curated/manifest.json --validate-only
   /private/tmp/mcele-demo-venv/bin/python scripts/deploy.py --plan
   ```

7. Deploy only through the existing isolated workflow:

   ```sh
   MCELE_DEMO_DEPLOY_APPROVED=1 /private/tmp/mcele-demo-venv/bin/python scripts/deploy.py --apply
   ```

8. Run the bounded scenario verifier using the new release ID printed by the plan/apply step:

   ```sh
   ssh velvux@atlas.tail65b4a7.ts.net \
     python3 /home/velvux/mcele-hackathon-demo/releases/<release-id>/scripts/verify_scenarios.py \
     --run \
     --synthetic-screenshot /home/velvux/mcele-hackathon-demo/releases/<release-id>/verification/synthetic-sts1.png
   ```

9. Manually verify in the public UI:

   - Instructor asks: `How do I copy a course in Moodle?`
   - Answer says AO role is required and directs the Instructor to obtain/contact an AO.
   - No tutorial link, AO steps, or MClearn reminder appears.
   - AO asks the same question and receives the full procedure plus the two approved links.
   - Switching profiles clears the prior transcript, course text, draft, image, and resolved context.

10. Verify the original app is still healthy and still reports 315 chunks. Update the current validation/deployment documents with the new release ID and results.

## Non-negotiable safety boundaries

- Treat `/home/velvux/ChatBotLLM` as read-only.
- Never stop/rebuild/reconfigure the original app, database, Langfuse infrastructure, or model-service containers.
- Never run Docker prune, broad Compose down, broad delete, or sync-delete commands.
- Keep demo database, vectors, sessions, volumes, network, containers, configuration, and credentials isolated.
- Do not print or copy `/home/velvux/.config/mcele-hackathon-demo/runtime.env`.
- Do not place credentials in prompts, logs, source, Git, or documentation.
- Do not perform concurrent inference/load tests against the shared GPU.
- Preserve the existing demo tunnel during normal updates when possible.

## Git/GitHub status and recommended approach

This is a separate project and should use a separate repository, not the original `ChatBotLLMPrototypeUSMCU` repository.

A new AI account on the same Mac does not require GitHub: reconnect the USB and open `/Volumes/USB_64_A/HackathonChatbot` as the Codex workspace.

For a safe local checkpoint before the grounding fix:

```sh
cd "/Volumes/USB_64_A/HackathonChatbot"
test ! -d .git && git init -b main
git status --short
git add -A
git diff --cached --stat
git diff --cached --check
git commit -m "checkpoint: deployed role-aware MCeLE demo c0e172cd39238e51"
```

Do not create a public repository yet. Article redistribution remains pending review. Before any remote push, inspect at least `knowledge/curated/articles/`, `docs/article-drafts/`, deployment records, and the entire staged diff for internal content and credentials.

After that review, a separate private repository can be created:

```sh
gh auth status
gh repo create mcele-hackathon-demo --private --source=. --remote=origin --push
```

Confirm the remote and branch:

```sh
git remote -v
git branch --show-current
git status
git log --oneline -3
```

## Ready-to-paste instruction for the next AI agent

> Continue the existing MCeLE hackathon demo; do not rebuild it. The source of truth is `/Volumes/USB_64_A/HackathonChatbot`, which must be mounted before edits. Read `AGENTS.md`, `README.md`, `docs/curated-validation.json`, `docs/atlas-deployment-record.json`, `docs/profiles-courses-and-access.md`, `docs/demo-decisions.md`, and `docs/deployment-review.md` first. The original Atlas project `/home/velvux/ChatBotLLM` is strictly read-only. The isolated demo root is `/home/velvux/mcele-hackathon-demo`; the currently recorded release is `c0e172cd39238e51`.
>
> The next task is one known grounding bug: a manual browser check showed that the Instructor answer fabricated `example.com/moodle-copy-tutorial` and mentioned AO training, although the Instructor source contains only permission guidance. No fix was applied because the USB disconnected. Fix this in the USB source, not on Atlas. Enforce that generated URLs and related tutorial/training claims must appear in the permission-filtered retrieved source. Add tests proving Instructor output contains no AO steps, tutorial, training reminder, or unsupported link, while AO output retains the approved tutorial and MClearn links. Review `ensure_citations` because blanket citation insertion can make unsupported claims look sourced.
>
> Run all local tests, ingestion validation, JavaScript syntax validation, and `scripts/deploy.py --plan`; deploy only with the existing isolated workflow; rerun `verify_scenarios.py`; manually compare Instructor versus AO responses; and verify the original app remains healthy with 315 chunks. Do not expose secrets, edit the original app, restart original services, run prune/cleanup commands, or load-test the shared GPU. No Git repository existed at the stopping point; create only a local checkpoint unless I explicitly approve a reviewed private remote.
