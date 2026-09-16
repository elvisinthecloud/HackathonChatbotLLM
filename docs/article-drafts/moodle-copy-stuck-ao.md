# Troubleshoot a Moodle course copy that is slow, stuck, or fails

## Article record

- Article ID: `MOODLE-COPY-003`
- Status: Added to the local curated dataset; not ingested or deployed
- Service/area: Moodle
- Allowed role: Academics Officer
- Course scope: General Moodle course-copy troubleshooting
- Content type: Adapted existing guidance, not synthetic
- Provenance: Atlas `/home/velvux/ChatBotLLM/knowledge/rag-source-documents/converted/LLM/moodle-course-copy-slow-policy-compliance.md`, selectively read on 2026-09-16; SHA-256 `28df99e1aa65644b6307649392f52ab4f265ca379e937b05d815777a1d7418cd`
- Local source cross-check: `/Users/elvis/Desktop/Hackathon Knowledge Base/converted/LLM-specific/moodle-course-copy-slow-policy-compliance.md`; byte-for-byte match with Atlas
- Redistribution status: To be confirmed before public submission packaging; no license inferred

## Knowledge content

Use this guidance when a Moodle course copy keeps loading, is extremely slow, times out, or fails. These symptoms can be related to the source course's design or compliance with MCeLE content-management policy.

1. Run the **Quality Assurance report** from the Moodle course. Review required course fields, activity and completion settings, enabled modules, and overall file usage.
2. Check for large audio or video files stored directly in Moodle. Move them to **Marine Video Services (MVS)**, then share them back into the Moodle course. See [How to upload a video or audio file to MVS and share it into Moodle](https://www.mcele.usmc.mil/MVS/watchVideo.aspx?Id=85395A47E9DC).
3. Check for large PDF, PowerPoint, or reference files stored directly in Moodle. Move them to the **Ecosystem Library**, then share them back into the course. See [How to upload files to the digital library and share them into Moodle](https://www.mcele.usmc.mil/MVS/watchVideo.aspx?Id=8113617D1A90).
4. Confirm that course-completion criteria are configured. Moodle courses must have defined completion criteria for completion, performance, enrollment, and attrition reporting.
5. Confirm that the required course custom fields are populated, including MCeLE Curriculum Code, MCeLE Course Code, Year, Section ID, Course Interval, Delivery Type, Cycle, Curriculum Version ID, Location, Course Purpose, and MCTIMS School Code.
6. Review the question bank for unused questions, outdated question versions, and questions from other course sources. Remove unused or outdated questions that are no longer needed. See [How to remove unused questions in a Moodle course question bank](https://www.mcele.usmc.mil/MVS/watchVideo.aspx?Id=891010D0FDB1).
7. Review quizzes for maximum-grade mismatches or other configuration issues.
8. Confirm that required Moodle role training is complete. Academics Officers must complete Marine Digital Educator Program courses **1100, 2100, and 3100**. Training is available in the [Marine Digital Educator Program category](https://elearning.mcele.usmc.mil/moodle/course/index.php?categoryid=1264).

Review the [MCeLE Content Management and Removal Policy](https://lmshelp.mcele.usmc.mil/jira/secure/attachment/74173/74173_Final+2026-2+MCeLE+Content+Management+and+Removal+Policy.pdf) when correcting course-content and hosting issues.

## Editorial and retrieval notes

- Keep this separate from `MOODLE-COPY-001`, which explains the normal copy procedure, and `MOODLE-COPY-002`, which gives Instructor permission guidance only.
- Restrict the article to the Academics Officer demo role before retrieval. An Instructor must not receive these troubleshooting steps through the demo.
- Do not claim a single root cause. The source says the listed design and policy problems can cause or contribute to slow, unreliable copies.
- Do not invent a cancel, reset, retry interval, browser fix, administrator action, or guaranteed resolution.
- Preserve the source URLs exactly. The demo has not independently verified that the linked resources are publicly accessible.
