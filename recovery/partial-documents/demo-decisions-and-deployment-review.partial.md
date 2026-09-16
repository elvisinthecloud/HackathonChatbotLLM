# Demo decisions

Updated 2026-09-14 from the user's scenario selections and procedure contributions. These decisions set product scope; they do not approve the first Atlas deployment. Later dated/checkpoint sections supersede earlier pending items where explicitly resolved.

## Access

Public access is required. Prepare a separate public route for the demo and include the concrete exposure method in the first deployment review. Do not modify the original application's route, tunnel, DNS, firewall, proxy, or ports. No public exposure has been configured.

## Five demo roles and scenarios

| UI role | Underlying role | Selected scenario |
| --- | --- | --- |
| Student | Student | Unable to launch CYBERM0000, described by the user as a biennial training course. Demonstrate screenshot input with the launch error. System/area is MCeLE (user confirmed). Selected error is `sts1.auth.ecuf.deas.mil refused to connect`; the matching live article was located. The error article applies across applicable MCeLE courses, not only CYBERM0000, and must exclude Moodle. A demonstration screenshot is still needed. |
| Instructor | Adjunct Faculty | Ask how to copy a course in Moodle. Explain that Academics Officer (AO) permissions are required and the instructor must obtain the appropriate permissions or contact a user with the AO role to perform the copy. Do not expose the copying procedure. |
| Academics Officer (AO) | Academics Officer | Ask the same Moodle course-copying question and receive the authorized copying instructions. AO is an additional role; it does not replace another role or imply role inheritance. |
| Regional Director | Regional Director | Presentation placeholder only, with no authored role-specific support scenario yet. Do not invent content or grant access by default. |
| Training Manager | Training Manager | Ask how to approve a student's PME seminar request. System/area is MCeLE (user confirmed). Related ECDEP command-approval and TM recommendation articles were found; exact TM click-by-click instructions remain to be verified. |

## Knowledge access and content preparation

- Use separate instructor-visible permission/escalation guidance and AO-only course-copy procedure content. The distinction must be enforced in backend retrieval, routing candidates, follow-ups, previews, and citations, before content reaches the LLM.
- These scenario-specific decisions do not establish a complete role/article permission matrix. Do not infer access for other roles. Missing permissions remain denied.
- The user's description supplies the desired instructor response, but does not supply real course-copy steps, the launch-error diagnosis, or the PME approval procedure. Obtain the selected articles or exact live-source paths/titles before packaging existing material.
- Read only selected relevant articles on Atlas. Do not copy the corpus or populated index. Record provenance and redistribution status for each selected source.
- Confirmed mappings: CYBERM0000 and PME seminar requests → MCeLE; Instructor/AO course copying → Moodle. Preserve MCeLE as the broader ecosystem while using these specific UI/routing area labels. No particular Moodle course has been selected. A recognized mention of CYBERM0000 can resolve to its server-controlled course record; explicit conflicting course selection requires clarification.
- Obtain an appropriate launch-error screenshot or a clearly labeled synthetic example. Do not invent a real error or present synthetic troubleshooting as verified guidance. Remove personal information and credentials from demonstration material.
- Public profile selection remains simulated identity, not production authentication. Curated content must be appropriate for public demonstration and redistribution even where the UI/backend restricts it to a selectable role.
- Start with the few articles needed to support these scenarios. The earlier roughly 10–15 article target remains provisional, not a requirement to invent filler.

## Still pending

Review of the authored Moodle and TM drafts; final selection/adaptation of located articles; launch-error screenshot; source video URLs and redistribution status for packaging; full explicit role/article permission matrix; course associations and their context/access meaning; public hosting route proposal and first deployment approval; separate Langfuse demo project credentials; ticket destination and supported fields (implementation last). Moodle copying and TM recommendation steps have now been supplied by the user.

## Source discovery checkpoint

See `article-discovery.md` for selected source candidates and content gaps. The `sts1` article is on live Atlas as well as the local reference. Existing CYBERM0000 mentions are mixed with CCE Annual Training examples and are not a clean dedicated course article. Moodle role training and slow-copy troubleshooting were found, but a basic course-copy procedure/tutorial has not yet been located. Do not confuse Moodle Academic Officer with MCeLE Approving Officer. TM recommendation versus subsequent regional action needs to be preserved accurately in the authored scenario. No original articles have been copied into the demo dataset.

## Course location versus delivery area

The user clarified that Moodle courses can be discovered through the MCeLE catalog and appear in a user's MCeLE courses before redirecting to Moodle. Portal location does not establish the system delivering the course.

Agreed direction: identify CYBERM0000 as MCeLE-delivered in the demo's server-controlled course catalog, while retaining MCeLE as its discovery portal. A Moodle course can also have MCeLE as its discovery portal, with Moodle as its delivery area. Proposed separate fields are `discovery_portal` and `delivery_area`; these describe demo context, not a live integration. The exact Moodle demo course is still to be supplied. Do not infer delivery area from catalog location, the user's broad use of the name MCeLE, or a role alone.

Resolve an explicit course selection or unambiguous known course-code mention against that server-controlled catalog. Clarify conflicts between selected course, mentioned course, and screenshot context. For an unknown course, ask for identifying context or inspect the screenshot/redirect evidence; do not guess its delivery area. Display the resolved area beside the course so a user can understand why the answer changes.

The user approved general MCeLE delivery scope for the sts1 error article with explicit Moodle exclusion. Course selection/mention supplies context; screenshot or supplied error text identifies the actual error. A vague launch failure must not automatically trigger this solution. Area applicability is separate from role authorization and course access permissions.

## Procedure clarifications

- The user will provide the actual Moodle course-copy procedure. Do not invent it or substitute generic Moodle documentation for the supplied workflow.
- The user confirmed the Training Manager action button says **Recommend**. Use that exact action in the TM scenario; the source describes subsequent regional action separately.
- The student-perspective article about being unable to select a TM is not needed for the TM scenario and must not be retrieved for it. It remains only an optional Student content candidate, not a selected dataset article.
- The ECDEP command-approval article contains a video link plus written troubleshooting for requests that do not display (Admin View, Clear Selected Role, Forms & Requests). It does not contain the actual click-by-click recommendation procedure. Whether that troubleshooting applies to the selected TM workflow remains unverified; do not include it automatically.

## Moodle procedure supplied and mappings accepted

The user accepted separate discovery-portal and delivery-area mappings. These remain server-controlled demo records; catalog appearance in MCeLE alone does not identify the delivery area.

The user supplied the Moodle copying transcript. Drafts are now available at `article-drafts/moodle-copy-course-ao.md` (AO-only steps) and `article-drafts/moodle-copy-permission-instructor.md` (Adjunct Faculty permission guidance). Timestamps were removed. Button labels, the two-overlapping-squares icon, the short-name example EWS 1349, and the Current Operation = Complete completion check are preserved. The example is not a seeded course.

The supplied source establishes the AO prerequisite for copying or creating courses, but contains only copying steps. No creation procedure or unspecified copy-form fields will be invented. Source video URL and redistribution status remain unresolved for packaging. The user is gathering ECDEP command-approval steps; the TM procedure remains pending, with Recommend already confirmed as the button label. Neither draft is ingested or deployed.

## TM procedure supplied

The user supplied and confirmed accurate the TM video-script steps. The draft at `article-drafts/mcele-ecdep-request-tm.md` is restricted to Training Manager and scoped to MCeLE ECDEP seminar enrollment requests.

The procedure is Administration → Requests; TYPE = Course Enrollment, REGION = All, STATUS = All Active; select Course enrollment beside the student; review completed fields; open Request file list and verify NAVMC Form 11580 plus prerequisite certification (which may be bundled inside the form); expand Decision, select, add comments, then Recommend or Deny. The page refresh after filter changes and Helpdesk fallback are preserved.

This completes the TM's action, not necessarily enrollment or regional processing. Do not invent Decision options, missing-document outcomes, prerequisite course details, or extra role-switching steps. The script's video URL was not supplied and must not be assumed to match the previously discovered video. Three user-supplied article drafts now exist, all awaiting review and none ingested or deployed.

## Article review: Instructor approved, AO links added

The user approved the Instructor course-copy permission guidance (`MOODLE-COPY-002`). Content approval does not grant first deployment approval.

The AO copying article (`MOODLE-COPY-001`) now includes the user-supplied tutorial, `https://portal.mcele.usmc.mil/content/mcele-portal/en/media/detail.html?Id=8527A2A4B6B0`, and ends with a reminder to complete the required MClearn training to avoid possible removal of AO permissions, linking to `https://elearning.mcele.usmc.mil/moodle/course/index.php?categoryid=1264`. These belong in answer content, not only provenance metadata. Preserve them with the procedure during ingestion/retrieval and verify both clickable links appear in an end-to-end AO course-copy answer once implemented.

The web tool could not open either supplied page, so no page contents or access requirements were independently verified. The URLs and training reminder come from the user. AO revised content and TM content remain awaiting review; the Student error article remains to be adapted. Nothing is ingested or deployed.

## TM seminar scope and AO wording comparison

The user limited the TM procedure to **5500 — Sergeants School Seminar Program** and **6800 — SNCO Leadership School Seminar**. These are user-supplied course codes/titles with MCeLE discovery and delivery mappings. `MCELE-ECDEP-001` now states this scope in both its record and knowledge content. Its allowed role remains Training Manager. Course applicability does not establish restrictions based on individual profile associations; those remain separate decisions. Do not apply these steps to other PME courses or Moodle merely because the user asks a general approval question.

The user asked to compare earlier AO training wording with the current reminder. The local reference `knowledge/rag-source-documents/converted/LLM/moodle-role-required-training.md` (also previously read on live Atlas) states that Moodle Academic Officers must complete Marine Digital Educator Program courses 1100, 2100, and 3100, and that failure to complete required role training or continued non-compliance with MCeLE content management policy can result i…3134 tokens truncated…ration changes. Images for the demo application may be built/pulled on Atlas; this does not rebuild original services.

Langfuse remains `http://host.docker.internal:3000` from the demo backend. A separate project named **MCeLE Hackathon Demo**, its project ID, and its API keys are required. Backend startup authenticates and verifies both project ID and name before emitting conversation traces. Keys must be entered privately on Atlas via `configure_runtime.py`; never in chat, USB source, or release archives. The separate project has been created: `cmu1njwr40003l808bk5ak05x`. Its private API-key configuration passed authenticated startup checks and end-to-end tracing. No existing project settings were changed.

## Isolation and sequencing

- Exact 28-file release allowlist; no original knowledge sources, drafts, secrets, Git history, caches, generated dependencies, backups, or macOS sidecars. Backend build context has its own allowlist. The allowlist is in `scripts/release_guard.py`.
- SHA-256 manifests are verified before staging and before application. Fixed canonical destination and root marker; symlinks and unexpected archive members are rejected. No broad deletion/extraction or sync to original source.
- Default `--plan`/`--check` are local-only. Explicit approved `--stage` uploads files without starting services. Explicit approved `--apply` stages, validates runtime and rendered Compose resource topology, checks collisions, and uses a deployment lock.
- Database DSN must match exact demo service/user/database and generated password, without URL overrides. Connection checks verify database/user plus an initialized demo identity marker. The original connection default was removed before source transfer.
- Only two explicitly listed synthetic records may be ingested. A wrong manifest, source path, permission list, service area, or non-synthetic article fails before DB writes. The original directory crawler/prune interface is removed. Re-indexing occurs transactionally in demo storage and refuses unexpected existing article IDs/datasets.
- Both candidate search and chunk search require the baseline dataset, IDs, explicit baseline permission, and synthetic metadata before returning any content. This is not the later five-role authorization implementation. Those articles are deliberately excluded until that work is done.
- Apply builds the new demo backend, stops only a previous demo backend/frontend/tunnel when updating, starts/updates demo DB, ingests the two articles, starts backend/frontend, verifies readiness and a single conversation/trace, and only then starts the new public tunnel.
- Inventory is saved before service mutations and records failures. Original frontend/backend/Langfuse health is checked before and after. Public URL accessibility and workstation-independent runtime must be checked after startup.
- Rollback verifies the inventory and resource ownership, removes only demo containers/network, and preserves its database volume, images, releases, and secrets. It never removes original resources. `rollback.py` defaults to a local plan, with no Docker or SSH access until `--apply`.

## Validation evidence and limits

Completed locally: 16 focused Python tests, source parsing, JavaScript syntax, synthetic manifest/content validation, installed dependency compatibility, and actual Docker Compose rendering using sample values. Tests cover missing/wrong DB configuration, symlinks/manifest boundaries, restricted content rejection from baseline, guards on both search paths, one-in-flight behavior, sanitized errors, Langfuse project mismatch, archive allowlisting/approval gate, and simulated transactional rollback on failed embedding.

A localhost UI preview with a synthetic response fixture verified chat submission, citations/source expansion, and the pending ticket panel visually. It did not contact the private VMs or generate traces. No local Docker daemon is running. The approved demo image built successfully on Atlas. Dedicated PostgreSQL execution, ingestion of exactly two synthetic articles, two sequential real conversations (host verifier and public browser), citations, and dedicated Langfuse traces all passed. Runtime inspection confirms all mounts/storage are on Atlas, with no workstation/USB paths. The exact Python 3.12 application package versions match the inspected live backend, but container execution still needs verification.

The four approved operational articles remain unindexed. Profiles, role/course enforcement, full transcript memory, and ticket prefilling are later stages per the agreed order. A fresh user screenshot is still needed for the Student scenario. No repository has been initialized.

## Approval recorded

User approved creation of only the resources and public exposure listed here, staging source into the fixed demo directory, provisioning dedicated demo credentials outside source, building the demo image, ingesting the two synthetic articles, and running one baseline conversation plus trace/health checks. Subsequent routine updates stay within these isolated demo resources. Any change to an original service or a new public-route architecture requires separate review.

## Hosted baseline checkpoint

Public URL: https://domain-heater-nelson-tours.trycloudflare.com (Quick Tunnel; may change after tunnel restart).

Original frontend/backend/Langfuse remain healthy, with original article chunk count 315. All four demo containers use the approved limits and `unless-stopped` restart policy. Idle snapshot after verification: backend about 71 MiB, database 36 MiB, frontend 5 MiB, tunnel 15 MiB; this is not a peak or load-test measurement.

Demo trace `938da2c1d02e6cfa554e5a8c1cc9786c` contains retrieval, routing, embedding, and chat observations. The public-browser interaction is also visible in the separate Langfuse project. Atlas records: `inventory.json`, `verification.json`, `runtime-verification.json`, and pre-start `image-preparation.json`; the USB snapshot is `atlas-runtime-verification.json`. The separate Langfuse project ID is `cmu1njwr40003l808bk5ak05x`; credentials are excluded.

To stop this release, preview the rollback plan and then run `python3 /home/velvux/mcele-hackathon-demo/releases/717fbd98c639da62/scripts/rollback.py --apply` on Atlas. Only demo containers/network are removed; the demo volume, image, releases, credentials, and separate Langfuse project are retained. No original resources are targeted.
