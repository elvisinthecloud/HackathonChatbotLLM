"""Ingest only the approved curated dataset into verified demo storage."""
from __future__ import annotations
import argparse
import hashlib
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



def embedding_fingerprint(document, model):
    inputs = [document['content']] if document.get('retrieval_text') else chunk_text(document['content'])
    if document.get('retrieval_text'): inputs.append(document['retrieval_text'])
    return {'embedding_model':model, 'embedding_input_sha256':hashlib.sha256(json.dumps(inputs,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()}


def index_status(documents, rows, embed_model):
    """Rows: (source_path, content_sha256, metadata, chunk_count). No network."""
    existing={row[0]:row for row in rows}
    stale=[]
    for d in documents:
        row=existing.get(d['source_path'])
        expected={**d['metadata'],**embedding_fingerprint(d,embed_model)}
        count=(1 if d.get('retrieval_text') else len(chunk_text(d['content'])))+bool(d.get('retrieval_text'))
        if not row or row[1]!=d['content_sha256'] or row[2]!=expected or row[3]!=count:
            stale.append(d['source_path'])
    extras=sorted(set(existing)-{d['source_path'] for d in documents})
    return {'current':not stale and not extras,'stale_article_ids':stale,'unexpected_article_ids':extras}


def check_index(manifest):
    config=validate_runtime()
    if manifest!=config.manifest: raise ValueError('Check requires configured manifest')
    documents=load_dataset(manifest)
    from db import init_pool,close_pool,get_connection
    init_pool()
    try:
        with get_connection() as conn:
            rows=conn.execute('SELECT a.source_path,a.content_sha256,a.metadata,count(c.id) FROM articles a LEFT JOIN article_chunks c ON c.article_id=a.id GROUP BY a.id').fetchall()
            return index_status(documents,rows,os.environ['OLLAMA_EMBED_MODEL'])
    finally: close_pool()


def reusable_embeddings(document, existing, model):
    if not existing: return False
    count=(1 if document.get('retrieval_text') else len(chunk_text(document['content'])))+bool(document.get('retrieval_text'))
    return existing[1]==document['content_sha256'] and existing[3]==count and all(existing[2].get(k)==v for k,v in embedding_fingerprint(document,model).items())


async def prepare_embeddings(documents, existing, model, client):
    """No DB transaction is held during model calls. None means reuse exact inputs."""
    prepared={}
    for d in documents:
        if reusable_embeddings(d,existing.get(d['source_path']),model):
            prepared[d['source_path']]=None
            continue
        inputs=[d['content']] if d.get('retrieval_text') else chunk_text(d['content'])
        units=list(enumerate(inputs))
        if d.get('retrieval_text'): units.append((-1,d['retrieval_text']))
        vectors=[]
        for index,content in units:
            response=await client.post(os.environ['OLLAMA_BASE_URL']+'/api/embed',json={'model':model,'input':content})
            if response.status_code!=200: raise RuntimeError('Demo embedding request failed')
            data=response.json();vector=(data.get('embeddings') or [data.get('embedding')])[0]
            if not isinstance(vector,list) or len(vector)!=768 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in vector):
                raise RuntimeError('Expected a finite 768-dimensional embedding')
            vectors.append((index,'' if index==-1 else content,vector))
        prepared[d['source_path']]=vectors
    return prepared


async def ingest(manifest: Path) -> dict:
    config=validate_runtime()
    if manifest!=config.manifest: raise ValueError('Ingestion requires the configured demo manifest')
    documents=load_dataset(manifest);validate_taxonomy(config.taxonomy)
    import httpx
    from db import close_pool,get_connection,init_pool
    from psycopg.types.json import Jsonb
    model=os.environ['OLLAMA_EMBED_MODEL']
    expected={d['source_path'] for d in documents}
    retired={'DEMO-BASELINE-NAV-001','DEMO-BASELINE-SMOKE-001'}
    query='SELECT a.source_path,a.content_sha256,a.metadata,count(c.id) FROM articles a LEFT JOIN article_chunks c ON c.article_id=a.id GROUP BY a.id'
    def validate_existing(rows):
        for source,_,metadata,_ in rows:
            if not ((source in expected and metadata.get('dataset_id')==DATASET_ID) or (source in retired and metadata.get('dataset_id')=='mcele-baseline-v1')):
                raise RuntimeError('Unexpected existing articles; refusing curated ingestion')
    init_pool()
    try:
        with get_connection() as conn:
            rows=conn.execute(query).fetchall();validate_existing(rows)
            existing={r[0]:r for r in rows}
        async with httpx.AsyncClient(timeout=60) as client:
            prepared=await prepare_embeddings(documents,existing,model,client)
        with get_connection() as conn:
            if not conn.execute('SELECT pg_try_advisory_xact_lock(684921)').fetchone()[0]:
                raise RuntimeError('Demo ingestion is already running')
            current=conn.execute(query).fetchall();validate_existing(current)
            current={r[0]:r for r in current}
            from demo_sessions import ensure_schema
            ensure_schema(conn)
            total=0;skipped=0
            for d in documents:
                vectors=prepared[d['source_path']]
                if vectors is None and not reusable_embeddings(d,current.get(d['source_path']),model):
                    raise RuntimeError('Index changed during preparation; retry ingestion')
                metadata={**d['metadata'],**embedding_fingerprint(d,model)}
                article_id=conn.execute(
                    """INSERT INTO articles(title,source_path,content_sha256,metadata) VALUES(%s,%s,%s,%s)
                    ON CONFLICT(source_path) DO UPDATE SET title=EXCLUDED.title,content_sha256=EXCLUDED.content_sha256,metadata=EXCLUDED.metadata,updated_at=now() RETURNING id""",
                    (d['title'],d['source_path'],d['content_sha256'],Jsonb(metadata))).fetchone()[0]
                total+=1 if d.get('retrieval_text') else len(chunk_text(d['content']))
                if vectors is None:
                    skipped+=1
                    continue
                conn.execute('DELETE FROM article_chunks WHERE article_id=%s',(article_id,))
                for index,content,vector in vectors:
                    conn.execute('INSERT INTO article_chunks(article_id,chunk_index,content,embedding,metadata) VALUES(%s,%s,%s,%s::vector,%s)',
                        (article_id,index,content,json.dumps(vector),Jsonb({'retrieval_only':True} if index==-1 else {})))
            conn.execute("DELETE FROM articles WHERE source_path=ANY(%s::text[]) AND metadata->>'dataset_id'='mcele-baseline-v1'",(sorted(retired),))
        return {'dataset_id':DATASET_ID,'article_ids':sorted(expected),'chunk_count':total,'unchanged_embeddings':skipped}
    finally: close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate-only", action="store_true", help="Check sources without DB, credentials or model calls")
    mode.add_argument("--check-only", action="store_true", help="Read-only index release/model/hash consistency check")
    args = parser.parse_args()
    if args.check_only:
        try:
            result=check_index(args.manifest)
        except Exception as exc:
            raise SystemExit('Demo index check failed ('+type(exc).__name__+'); details withheld to protect configuration') from None
        print(json.dumps(result))
        raise SystemExit(0 if result["current"] else 1)
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
