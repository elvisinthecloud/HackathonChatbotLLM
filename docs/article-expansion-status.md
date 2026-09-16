# Article expansion status — 2026-09-16

The clean GitHub recovery began with four deployed curated articles. This work expands the isolated hackathon dataset to seven source-supported articles. Release `fab13e75b00fb0ab` was deployed and ingested on Atlas on 2026-09-16. The original chatbot remained healthy with 315 chunks.

| Scenario | Article ID | Local dataset | Source status | Remaining decision |
| --- | --- | --- | --- | --- |
| Student MCeLE launch error | `MCELE-LAUNCH-001` | Included | Previously approved | None |
| Instructor Moodle copy permission | `MOODLE-COPY-002` | Included | Previously approved | None |
| AO normal Moodle copy | `MOODLE-COPY-001` | Included | Previously approved | None |
| TM ECDEP Recommend/Deny | `MCELE-ECDEP-001` | Included | Previously approved | None |
| AO slow/stuck Moodle copy | `MOODLE-COPY-003` | Included and live-tested | Verified Atlas article | None |
| TM verify enrollment status | `MCELE-ENROLLMENT-REPORT-001` | Included and deployed | Verified Atlas report article plus approved scenario | Live scenario test pending |
| Student repeat course for RRC | `MCELE-RRC-001` | Included and deployed | Confirmed Help Desk answer plus verified catalog guidance | Live scenario test pending |
| Student CSC missing enrollment | `MCELE-CSC-001` | Excluded | Verified access sources plus user routing requirements | Choose Moodle-side escalation order |
| Student EPME after MOL selection | `MCELE-EPME-001` | Excluded | No dedicated source found | Supply prerequisites, owner, action, and escalation path |

Relevant local knowledge-base files were compared to the original Atlas files by SHA-256 and matched byte-for-byte. Corpus searches were read-only. No full corpus, vector index, database, secret, or ticket record was copied into this repository.

The GitHub recovery lacked `tests/test_backend.py`, which is imported by the recovered grounding and session tests. A minimal bootstrap was restored from the exact preserved prefix in `recovery/partial-documents/test_backend.partial.txt`. It restores the fake offline environment and patched app import only; the missing historical backend test cases have not been reconstructed.
