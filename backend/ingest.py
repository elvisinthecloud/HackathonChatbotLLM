"""Ingest only the approved curated dataset into verified demo storage."""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path

from demo_config import validate_runtime, DATASET_ID
from demo_dataset import load_dataset, validate_taxonomy

def chunk_text(text: str, max_words: int = 260, overlap_words: int = 50) -> list[str]:
    if max_words <= 0:
        raise ValueError("max_words must be greater than 0.")
    if overlap_words < 0:
        raise ValueError("overlap_words cannot be negative.")
    if overlap_words >= max_words:
        raise ValueError("overlap_words must be smaller than max_words.")

    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += max_words - overlap_words
    return chunks



async def ingest(manifest: Path) -> dict:
    config = validate_runtime()
    if manifest != config.manifest:
        raise ValueError("Ingestion requires the configured demo manifest")
    documents = load_dataset(manifest)
    validate_taxonomy(config.taxonomy)
    import httpx
    from db import close_pool, get_connection, init_pool
    from psycopg.types.json import Jsonb

    init_pool()
    try:
        with get_connection() as conn:
            # One transaction and one ingestion process: no partial dataset swaps.
            if not conn.execute("SELECT pg_try_advisory_xact_lock(684921)").fetchone()[0]:
                raise RuntimeError("Demo ingestion is already running")
            rows = conn.execute("SELECT source_path, metadata FROM articles").fetchall()
            expected = {d["source_path"] for d in documents}
            retired = {"DEMO-BASELINE-NAV-001", "DEMO-BASELINE-SMOKE-001"}
            for source, metadata in rows:
                if not ((source in expected and metadata.get("dataset_id") == DATASET_ID) or (source in retired and metadata.get("dataset_id") == "mcele-baseline-v1")):
                    raise RuntimeError("Unexpected existing articles; refusing curated ingestion")
            from demo_sessions import ensure_schema
            ensure_schema(conn)
            total = 0
            async with httpx.AsyncClient(timeout=60) as client:
                for document in documents:
                    # Reuse source chunking and Ollama embed API, but embed CONTENT ONLY.
                    chunks = chunk_text(document["content"])
                    vectors = []
                    for content in chunks:
                        response = await client.post(
                            os.environ["OLLAMA_BASE_URL"] + "/api/embed",
                            json={"model": os.environ["OLLAMA_EMBED_MODEL"], "input": content},
                        )
                        if response.status_code != 200:
                            raise RuntimeError("Demo embedding request failed")
                        data = response.json()
                        vector = (data.get("embeddings") or [data.get("embedding")])[0]
                        if not isinstance(vector, list) or len(vector) != 768 or any(
                            not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector
                        ):
                            raise RuntimeError("Expected a finite 768-dimensional embedding")
                        vectors.append(vector)
                    article_id = conn.execute(
                        """INSERT INTO articles(title, source_path, content_sha256, metadata)
                           VALUES (%s, %s, %s, %s)
                           ON CONFLICT(source_path) DO UPDATE SET title=EXCLUDED.title,
                           content_sha256=EXCLUDED.content_sha256, metadata=EXCLUDED.metadata, updated_at=now()
                           RETURNING id""",
                        (document["title"], document["source_path"], document["content_sha256"], Jsonb(document["metadata"])),
                    ).fetchone()[0]
                    # Deletes are scoped to one validated allowlisted article, never broad prune.
                    conn.execute("DELETE FROM article_chunks WHERE article_id=%s", (article_id,))
                    for index, (content, vector) in enumerate(zip(chunks, vectors)):
                        conn.execute(
                            "INSERT INTO article_chunks(article_id,chunk_index,content,embedding) VALUES(%s,%s,%s,%s::vector)",
                            (article_id, index, content, json.dumps(vector)),
                        )
                        total += 1
            # The only retirement is the two named synthetic records, in this same transaction.
            conn.execute("DELETE FROM articles WHERE source_path=ANY(%s::text[]) AND metadata->>'dataset_id'='mcele-baseline-v1'", (sorted(retired),))
            return {"dataset_id": DATASET_ID, "article_ids": sorted(expected), "chunk_count": total}
    finally:
        close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true", help="Check sources without DB, credentials or model calls")
    args = parser.parse_args()
    if args.validate_only:
        documents = load_dataset(args.manifest)
        validate_taxonomy(args.manifest.parent / "taxonomy.json")
        print(json.dumps({"valid": True, "article_ids": [d["source_path"] for d in documents]}))
    else:
        import anyio
        try:
            print(json.dumps(anyio.run(ingest, args.manifest)))
        except Exception as exc:
            # Don't print driver/HTTP exception strings: they can contain connection configuration.
            raise SystemExit("Demo ingestion failed (" + type(exc).__name__ + "); verify demo configuration and health") from None


if __name__ == "__main__":
    main()
