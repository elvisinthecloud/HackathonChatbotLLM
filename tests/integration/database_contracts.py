"""Integration probe against a disposable localhost PostgreSQL test container.
Uses synthetic vectors, never calls a real model or application VM.
"""
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'backend')]
import support
import os
os.environ.update(support.test_env())
import psycopg
from psycopg.types.json import Jsonb
import db, rag, ingest, demo_sessions
from demo_dataset import load_dataset
from demo_policy import ACCESS, RetrievalAccess
MANIFEST=ROOT/'knowledge/curated/manifest.json'
PORT = None
REPORT_PATH = ROOT / "output/test-suite-refresh/database-results.json"
@contextmanager
def connection():
    with psycopg.connect(host='127.0.0.1',port=PORT,user='mcele_demo',password='local-test-only',dbname='mcele_demo') as conn:
        yield conn

async def main():
    report={'environment':'disposable localhost PostgreSQL16 + pgvector','vectors':'synthetic; no semantic quality claim','checks':[]}
    response=MagicMock(status_code=200)
    response.json.return_value={'embeddings':[[1.0]+[0.0]*767]}
    client=MagicMock()
    client.post=AsyncMock(return_value=response)
    client.__aenter__=AsyncMock(return_value=client)
    client.__aexit__=AsyncMock(return_value=None)
    cfg=SimpleNamespace(manifest=MANIFEST,taxonomy=MANIFEST.parent/'taxonomy.json')
    with patch.object(db,'get_connection',connection), patch.object(db,'init_pool'), patch.object(db,'close_pool'), patch.object(ingest,'validate_runtime',return_value=cfg), patch('httpx.AsyncClient',return_value=client):
        first=await ingest.ingest(MANIFEST)
        calls=client.post.await_count
        second=await ingest.ingest(MANIFEST)
        assert second['unchanged_embeddings']==19 and client.post.await_count==calls
        report['checks'].append({'check':'atomic ingestion and unchanged vector reuse','status':'passed','articles':19,'first_embedding_calls':calls,'second_embedding_calls':0})
    docs=load_dataset(MANIFEST)
    with connection() as conn:
        rows=conn.execute('SELECT a.source_path,a.content_sha256,a.metadata,count(c.id) FROM articles a LEFT JOIN article_chunks c ON c.article_id=a.id GROUP BY a.id').fetchall()
        assert ingest.index_status(docs,rows,rag.settings.embed_model)['current']
    report['checks'].append({'check':'canonical release/hash/model/index consistency','status':'passed'})
    with patch.object(rag,'get_connection',connection),patch.object(rag,'langfuse',MagicMock()):
        token=ACCESS.set(RetrievalAccess('Student','Moodle',None,tuple(d['source_path'] for d in docs)))
        try:
            lexical=rag.search_lexical_article_candidates('Can you please help me copy a course in Moodle?',12)
            vector=rag.search_article_candidates([1.0]+[0.0]*767,12)
        finally: ACCESS.reset(token)
        for hit in lexical+vector:
            assert 'Student' in hit['article_metadata']['allowed_roles']
            assert hit['article_metadata']['service_area']=='Moodle'
            assert hit['source_path'] not in {'MOODLE-COPY-001','MOODLE-COPY-002','MOODLE-COPY-003'}
            assert hit['content_sha256']
        assert lexical and vector
        report['checks'].append({'check':'real vector and lexical SQL filter role/area before returning metadata','status':'passed','lexical_hits':len(lexical),'vector_hits':len(vector)})
    with patch.object(demo_sessions,'get_connection',connection):
        created=demo_sessions.create_session('student',None)
        s1=demo_sessions.load_session(created['session_id'])
        s2=demo_sessions.load_session(created['session_id'])
        result={'answer':'test response','response_kind':'support'}
        demo_sessions.save_turn(s1,None,{'conversation':{}},False,'test user','',False,result)
        try:
            demo_sessions.save_turn(s2,None,{},False,'stale user','',False,result)
            raise AssertionError('stale write accepted')
        except demo_sessions.SessionConflict: pass
        after=demo_sessions.load_session(created['session_id'])
        assert after['revision']==1 and len(after['turns'])==1
        report['checks'].append({'check':'stale concurrent session cannot write context or turn','status':'passed','persisted_turns':1})
    # Controlled synthetic corpus: this checks SQL bounds and access filtering,
    # not retrieval relevance, LLM behavior, or permission grants of real sources.
    with connection() as conn:
        for i in range(300):
            metadata={'dataset_id':'mcele-curated-v1','allowed_roles':['Student' if i<250 else 'Academics Officer'],'service_area':'MCeLE'}
            aid=conn.execute('INSERT INTO articles(source_path,title,content_sha256,metadata) VALUES(%s,%s,%s,%s) RETURNING id',(f'SCALE-{i}',f'Course launch {i}','synthetic',Jsonb(metadata))).fetchone()[0]
            conn.execute('INSERT INTO article_chunks(article_id,chunk_index,content,embedding) VALUES(%s,0,%s,%s::vector)',(aid,'Course launch guidance synthetic '+str(i),json.dumps([1.0]+[0.0]*767)))
    with patch.object(rag,'get_connection',connection),patch.object(rag,'langfuse',MagicMock()):
        token=ACCESS.set(RetrievalAccess('Student','MCeLE',None,tuple(f'SCALE-{i}' for i in range(300))))
        try:
            lexical=rag.search_lexical_article_candidates('course launch',12)
            vector=rag.search_article_candidates([1.0]+[0.0]*767,12)
        finally: ACCESS.reset(token)
        assert len(lexical)==len(vector)==12
        assert all(int(h['source_path'].split('-')[1])<250 for h in lexical+vector)
        report['checks'].append({'check':'300 synthetic database articles: bounded searches exclude 50 forbidden sources','status':'passed','vector_hits':12,'lexical_hits':12})
    report['live_model_calls']=0
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

def run_disposable_database():
    import argparse
    import subprocess
    import time
    import uuid
    global PORT, REPORT_PATH
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true',help='Start a disposable local Docker database and run integration checks')
    parser.add_argument('--output',type=Path,default=REPORT_PATH)
    args=parser.parse_args()
    if not args.run:
        parser.print_help()
        return
    REPORT_PATH=args.output.resolve()
    # No context override: explicitly require local Docker Desktop instead of
    # risking a developer's remote Docker context.
    context=subprocess.run(['docker','context','show'],check=True,capture_output=True,text=True).stdout.strip()
    endpoint=subprocess.run(['docker','context','inspect',context,'--format','{{.Endpoints.docker.Host}}'],check=True,capture_output=True,text=True).stdout.strip()
    if not endpoint.startswith('unix://') or os.environ.get('DOCKER_HOST') or os.environ.get('DOCKER_CONTEXT'):
        raise SystemExit('Use a local Unix-socket Docker context without environment overrides.')
    name='mcele-contract-test-'+uuid.uuid4().hex[:10]
    started=False
    try:
        subprocess.run(['docker','run','--detach','--rm','--name',name,'--memory','512m','--cpus','1','--tmpfs','/var/lib/postgresql/data',
            '-e','POSTGRES_USER=mcele_demo','-e','POSTGRES_DB=mcele_demo','-e','POSTGRES_PASSWORD=local-test-only',
            '-p','127.0.0.1::5432','pgvector/pgvector:pg16'],check=True,capture_output=True)
        started=True
        for _ in range(50):
            ready=subprocess.run(['docker','exec',name,'pg_isready','-h','127.0.0.1','-U','mcele_demo','-d','mcele_demo'],capture_output=True)
            if ready.returncode==0:break
            time.sleep(.2)
        else:raise RuntimeError('Disposable database did not become ready')
        PORT=int(subprocess.run(['docker','port',name,'5432'],check=True,capture_output=True,text=True).stdout.strip().rsplit(':',1)[1])
        subprocess.run(['docker','exec','-i',name,'psql','-U','mcele_demo','-d','mcele_demo','-v','ON_ERROR_STOP=1'],
            input=(ROOT/'database/schema.sql').read_bytes(),check=True,capture_output=True)
        asyncio.run(main())
    finally:
        if started:
            subprocess.run(['docker','stop','--timeout','3',name],check=True,capture_output=True)

if __name__ == '__main__':
    run_disposable_database()

