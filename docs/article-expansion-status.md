# Article expansion status — 2026-09-16

The clean GitHub recovery began with four deployed curated articles. Release `34e27280c7bae06d` contains seven deployed articles. An eighth source-supported EPME policy article is included locally for review. The original chatbot remained healthy with 315 chunks.

| Scenario | Article ID | Local dataset | Source status | Remaining decision |
| --- | --- | --- | --- | --- |
| Student MCeLE launch error | `MCELE-LAUNCH-001` | Included | Previously approved | None |
| Instructor Moodle copy permission | `MOODLE-COPY-002` | Included | Previously approved | None |
| AO normal Moodle copy | `MOODLE-COPY-001` | Included | Previously approved | None |
| TM ECDEP Recommend/Deny | `MCELE-ECDEP-001` | Included | Previously approved | None |
| AO slow/stuck Moodle copy | `MOODLE-COPY-003` | Included and live-tested | Verified Atlas article | None |
| TM verify enrollment status | `MCELE-ENROLLMENT-REPORT-001` | Included and live-tested | Verified Atlas report article plus approved scenario | None |
| Student repeat course for RRC | `MCELE-RRC-001` | Included and live-tested | Confirmed Help Desk answer plus verified catalog guidance | None |
| Student CSC missing enrollment | `MCELE-CSC-001` | Excluded | Verified access sources plus user routing requirements | Choose Moodle-side escalation order |
| Student EPME eligibility after MOL selection | `MCELE-EPME-001` | Included locally; not deployed | User-confirmed MCTFS/MOL behavior plus official CDET and MARADMIN policy | Review condensed article and live replies |

Relevant local knowledge-base files were compared to the original Atlas files by SHA-256 and matched byte-for-byte. Corpus searches were read-only. No full corpus, vector index, database, secret, or ticket record was copied into this repository.

The GitHub recovery lacked `tests/test_backend.py`, which is imported by the recovered grounding and session tests. A minimal bootstrap was restored from the exact preserved prefix in `recovery/partial-documents/test_backend.partial.txt`. It restores the fake offline environment and patched app import only; the missing historical backend test cases have not been reconstructed.
