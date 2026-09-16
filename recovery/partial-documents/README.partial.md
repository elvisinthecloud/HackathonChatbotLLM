# MCeLE Support Demo

A standalone hackathon demo scaffolded from the live Atlas chatbot. It reuses FastAPI, pgvector/Postgres, the existing Ollama models, and the existing Langfuse instance. It has its own application configuration, database, vectors, profiles, sessions, frontend, and public tunnel. The original application is protected and unchanged.

The current demo supports five selectable profiles and four approved articles. Course selection accepts a code/name, and the user's task determines the system: for example, 5500 enrollment is on MCeLE while course content is on Moodle. See [profiles, courses, access, and memory](docs/profiles-courses-and-access.md). Ticket prefilling is intentionally pending the destination page and fields. No repository has been initialized.

## Working directory and development dependencies

The USB workspace is the source of truth: edit here, then deploy an allowlisted release to the isolated Atlas demo directory. USB is an exFAT development filesystem, not a runtime host. The deployed application does not depend on it or on the workstation.

Use Python 3.12 for application development. The workstation's default Python is 3.14; this session uses a native-filesystem environment at `/private/tmp/mcele-demo-venv`, Python under `/private/tmp/mcele-demo-python`, uv under `/private/tmp/mcele-demo-tools`, and cache under `/private/tmp/mcele-demo-cache`. These temporary directories may be removed by the OS; recreate them as needed outside the USB. Do not store virtual environments or caches on exFAT. The exact 48 application package versions are pinned in `backend/requirements.lock` to the inspected live backend versions. Docker and Docker Compose are needed for deployment validation and Atlas execution. Node is used only for JavaScript syntax validation; there is no frontend build step.

From the project root, using your native-filesystem Python 3.12 environment:

```sh
python -m pip install -r backend/requirements.lock
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -q
node --check frontend/chat-widget.js
python backend/ingest.py --manifest knowledge/curated/manifest.json --validate-only
python scripts/deploy.py --plan
```

Do not run the application directly with invented/default credentials. Deployment configuration fails closed unless it targets the dedicated demo database and existing model endpoints. Offline tests mock external services and use fake configuration values; they do not contact Atlas or run inference. Local Compose rendering uses sample configuration and does not require a Docker daemon. The workstation Docker daemon was unavailable in this session; container execution is verified on Atlas.

## Data and source provenance

The four original approved drafts remain in `docs/article-drafts/`. Their Knowledge content alone is copied into JSON records under `knowledge/curated/articles/`; records carry IDs, permissions, course scope, provenance, and redistribution status separately. Metadata and editorial notes are not embedded. `knowledge/curated/manifest.json` is an exact allowlist, not a directory crawl. Taxonomy is limited to the three reviewed areas. Ingestion refuses wrong roles/scopes, extra manifest files, symlinks, or unexpected existing index records.

The original corpus, populated vector index, production data, Git history, backups, and secrets were never copied. Only 13 allowlisted application files were initially scaffolded from the verified deployment; see `docs/source-provenance.json`. The two synthetic baseline articles remain in USB history material under `knowledge/baseline`, but are excluded from the current release and removed from demo search storage by the explicit named migration.

The synthetic screenshot in `verification/synthetic-sts1.png` tests the real vision model without claiming to be an actual service screenshot. Regenerate it with `python verification/make_screenshot_fixture.py` using Pillow outside the app environment if needed. The image is packaged for the bounded verifier, not ingested. The user's intended real screenshot still needs a final scenario check when supplied.

Approved demo use does not establish a redistribution license. Confirm article redistribution before creating the public submission repository. Keep future repository packaging free of credentials, private data, generated dependencies, database storage, `.DS_Store`, and `._*` sidecars.

## Approved deployment workflow

The user approved the isolated deployment and separate public tunnel, with combined runtime ceilings of 2.75 CPUs / 2.25 GiB RAM. Routine changes within these resources are authorized. See [deployment review](docs/deployment-review.md), [current verification](docs/curated-validation.json), and `AGENTS.md`.

Atlas target is `velvux@atlas.tail65b4a7.ts.net`. Demo root is `/home/velvux/mcele-hackathon-demo`, Compose project `mcele-hackathon-demo`. Never deploy into `/home/velvux/ChatBotLLM` or run that project's Compose commands. No broad deletion, prune, original-service restart, or original-route change is permitted.

1. Edit and run the local checks above. `scripts/deploy.py --plan` prints the content-hashed release path and validates actual Compose mounts, project names, volumes, ports, and resource caps. The allowlist is in `scripts/release_guard.py`.
2. Private configuration already exists on Atlas at `/home/velvux/.config/mcele-hackathon-demo/runtime.env` (0600, parent 0700). It uses only dedicated demo credentials and the separate **MCeLE Hackathon Demo** Langfuse project, ID `cmu1njwr40003l808bk5ak05x`. Do not rerun provisioning or overwrite the file for routine updates. For a fresh approved environment, stage first, then use `scripts/configure_runtime.py` interactively on Atlas; its credential prompts are hidden.
3. Apply the checked USB release:

   ```sh
   MCELE_DEMO_DEPLOY_APPROVED=1 python3 scripts/deploy.py --apply
   ```

   Apply stages explicit files, verifies hashes/runtime/ownership/capacity/original health, builds only the demo image, pauses only demo application services, ingests only approved demo data transactionally, and starts the demo backend/frontend. It verifies an Instructor conversation and its dedicated trace. The existing demo tunnel is preserved on routine updates while running; if absent/stopped, only that demo tunnel is started. Current original frontend/backend/Langfuse health is checked again before success.
4. Check the public page and, when needed, run the bounded scenario verifier on Atlas, replacing `<release-id>` with the current printed hash:

   ```sh
   ssh velvux@atlas.tail65b4a7.ts.net python3 /home/velvux/mcele-hackathon-demo/releases/<release-id>/scripts/verify_scenarios.py --run --synthetic-screenshot /home/velvux/mcele-hackathon-demo/releases/<release-id>/verification/synthetic-sts1.png
   ```

   This runs sequential normal requests, not a load test. Do not run concurrent inference checks that could disrupt the original chatbot's shared GPU.

The public URL can be read from `docker logs --tail 80 mcele-hackathon-demo-tunnel` on Atlas. Never dump backend environment variables or credential files. A Quick Tunnel URL may change when its process restarts; a stable named route needs separate review. The temporary workstation SSH forward on port 13000 is only for viewing Langfuse locally and is not an application dependency.

## Inventory, rollback, and persistent state

Atlas inventory and verification reports live in the demo root. Each release has a `release-hashes.json`. New resources use the `mcele-hackathon-demo` prefix: backend/frontend/db/tunnel containers, `mcele-hackathon-demo-network`, `mcele-hackathon-demo-postgres-data`, and backend images tagged by release. Postgres contains `articles`, `article_chunks`, the identity marker, `demo_sessions`, and `demo_turns` in the dedicated `mcele_demo` database only. The Langfuse demo project is a separate API resource on the shared instance.

To inspect the rollback plan, then stop only the demo if desired:

```sh
# On Atlas; replace <release-id> with the current release:
python3 /home/velvux/mcele-hackathon-demo/releases/<release-id>/scripts/rollback.py
python3 /home/velvux/mcele-hackathon-demo/releases/<release-id>/scripts/rollback.py --apply
```

Rollback validates exact inventory, project labels, and network attachments before removing only demo containers/network. It retains demo database data, releases, images, configuration, and the Langfuse project. It does not reverse data migrations or delete t…11438 tokens truncated…
      },
      {
        "name": "mcele-hackathon-demo-frontend",
        "running": true,
        "restart_policy": "unless-stopped",
        "cpu_limit": 0.25,
        "ram_limit_mib": 256.0,
        "mounts": [
          {
            "source": "/home/velvux/mcele-hackathon-demo/releases/c0e172cd39238e51/frontend/nginx.conf",
            "target": "/etc/nginx/conf.d/default.conf",
            "type": "bind",
            "writable": false
          },
          {
            "source": "/home/velvux/mcele-hackathon-demo/releases/c0e172cd39238e51/frontend",
            "target": "/usr/share/nginx/html",
            "type": "bind",
            "writable": false
          }
        ]
      },
      {
        "name": "mcele-hackathon-demo-tunnel",
        "running": true,
        "restart_policy": "unless-stopped",
        "cpu_limit": 0.25,
        "ram_limit_mib": 256.0,
        "mounts": []
      }
    ],
    "article_ids": [
      "MCELE-ECDEP-001",
      "MCELE-LAUNCH-001",
      "MOODLE-COPY-001",
      "MOODLE-COPY-002"
    ],
    "health": {
      "8000": {
        "ok": true,
        "chunk_count": 315
      },
      "8081": {
        "ok": true,
        "chunk_count": 4
      }
    },
    "course_change_transcript_retained": true,
    "backend_images": [
      "mcele-hackathon-demo-backend:c0e172cd39238e51",
      "mcele-hackathon-demo-backend:da1a16ad9ac0ac10",
      "mcele-hackathon-demo-backend:ed7ce6d5a051864e",
      "mcele-hackathon-demo-backend:717fbd98c639da62"
    ],
    "public_url": "https://domain-heater-nelson-tours.trycloudflare.com",
    "runtime_dependency_check": "All source/config mounts and database storage are on Atlas; no workstation or USB mounts"
  }
}
