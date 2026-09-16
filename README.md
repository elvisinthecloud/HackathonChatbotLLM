# MCeLE Support Hackathon Demo

This project is an isolated, role-aware support chatbot built for a hackathon demonstration. It uses a small curated knowledge base, embedding retrieval, explicit role permissions, and cited answers to show how MCeLE and Moodle support guidance can be delivered safely.

## Demo scenarios

The curated dataset contains nine scenarios:

1. Student — troubleshoot the approved MCeLE course-launch error.
2. Instructor / Adjunct Faculty — request permission to copy a Moodle course.
3. Academics Officer — copy a Moodle course.
4. Training Manager — recommend or deny an ECDEP seminar enrollment request.
5. Academics Officer — troubleshoot a slow or stuck Moodle course copy.
6. Student — access CSC and troubleshoot a missing Moodle enrollment.
7. Student — check EPME course eligibility and enrollment requirements.
8. Training Manager — verify a Marine's enrollment status.
9. Student — determine whether a completed course can earn Reserve Retirement Credits again.

Submission-ready text articles are in [`hackathon-dataset`](hackathon-dataset), with a ready-to-upload [`hackathon-dataset.zip`](hackathon-dataset.zip). The archive contains nine `.txt` files with only an Article record and Knowledge content; internal editorial and retrieval notes are excluded.

## Pipeline

1. Curated articles are validated, split into answer chunks, embedded with Ollama, and stored in PostgreSQL with pgvector.
2. The user selects a demo role and may provide a course. The backend resolves the task and system from server-owned policy.
3. Role, course, and system filters limit which articles are eligible before semantic similarity search runs.
4. The local chat model answers from the permitted excerpts and adds citations.
5. Grounding checks citations and links before returning the answer. Demo conversations can be traced with Langfuse.

## Project structure

- `backend/` — FastAPI chatbot, role policy, retrieval, grounding, and ingestion.
- `frontend/` — Browser-based demo interface.
- `knowledge/curated/` — Runtime JSON dataset and taxonomy.
- `hackathon-dataset/` — Plain-text dataset prepared for hackathon upload.
- `hackathon-dataset.zip` — Zip archive containing the nine upload-ready `.txt` articles.
- `tests/` — Offline routing, grounding, session, and dataset checks.
- `scripts/` — Guarded deployment and verification tools for the isolated demo.

## Validation

Run the offline checks from the repository root:

```bash
python -m unittest discover -s tests -v
python backend/ingest.py --manifest knowledge/curated/manifest.json --validate-only
```

The demo requires Python 3.12 for the application environment. Dependencies are pinned in `backend/requirements.lock`.

## Isolation

The hackathon demo uses its own containers, database, vector data, sessions, configuration, and tracing project. Runtime credentials are not stored in this repository. The separate operational chatbot and its knowledge base are outside this project's deployment scope.
