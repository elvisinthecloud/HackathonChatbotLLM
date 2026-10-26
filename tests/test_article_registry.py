"""Offline release, authorization and incremental-index contracts."""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from demo_dataset import load_dataset, DatasetError
from article_registry import read_registry
from article_retrieval import authorized_ids, applicability_status, hybrid_rank
from ingest import embedding_fingerprint, index_status, chunk_text

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()/'curated'
        shutil.copytree(ROOT/'knowledge/curated',self.root)
        self.path=self.root/'manifest.json'
    def mutate(self,fn):
        m=json.loads(self.path.read_text());fn(m);self.path.write_text(json.dumps(m))
    def test_missing_grants_and_duplicate_ids_fail_closed(self):
        self.mutate(lambda m:m['articles'][0].pop('allowed_roles'))
        with self.assertRaises(DatasetError):load_dataset(self.path)
    def test_duplicate_ids_fail_closed(self):
        self.mutate(lambda m:m['articles'].append(copy.deepcopy(m['articles'][0])))
        with self.assertRaises(DatasetError):load_dataset(self.path)
    def test_changed_file_invalidates_cached_snapshot(self):
        load_dataset(self.path)
        file=self.root/read_registry(self.path)['articles'][0]['file']
        file.write_text(file.read_text()+' ')
        with self.assertRaises(DatasetError):load_dataset(self.path)
    def test_new_reviewed_article_requires_no_python_registry_edit(self):
        m=json.loads(self.path.read_text());e=copy.deepcopy(m['articles'][0]);a=json.loads((self.root/e['file']).read_text())
        a['article_id']='NEW-REVIEWED-001';e['article_id']=a['article_id'];e['file']='articles/new.json'
        raw=json.dumps(a).encode();(self.root/e['file']).write_bytes(raw);e['file_sha256']=hashlib.sha256(raw).hexdigest()
        m['articles'].append(e);self.path.write_text(json.dumps(m))
        self.assertEqual(len(load_dataset(self.path)),20)
    def test_authorization_separate_from_course_applicability(self):
        self.assertIn('MCELE-CSC-001',authorized_ids('Student'))
        doc=next(d for d in load_dataset(self.path) if d['source_path']=='MCELE-CSC-001')
        self.assertEqual(applicability_status(doc['metadata'],{})['missing'],['course_id'])
        self.assertFalse(applicability_status(doc['metadata'],{'course_id':'5500'})['applicable'])
        self.assertTrue(applicability_status(doc['metadata'],{'course_id':'CSC'})['applicable'])
        self.assertNotIn('MOODLE-COPY-001',authorized_ids('Student'))
    def test_index_hash_and_embedding_model_are_required(self):
        docs=load_dataset(self.path);model='nomic-embed-text'
        rows=[(d['source_path'],d['content_sha256'],{**d['metadata'],**embedding_fingerprint(d,model)},2 if d['retrieval_text'] else len(chunk_text(d['content']))) for d in docs]
        self.assertTrue(index_status(docs,rows,model)['current'])
        self.assertFalse(index_status(docs,rows,'other-model')['current'])
        rows[0][2]['release_sha256']='stale'
        self.assertFalse(index_status(docs,rows,model)['current'])
    def test_large_candidate_set_bounded_without_unauthorized_candidates(self):
        base=load_dataset(self.path)[0];docs={};candidates=[]
        for i in range(300):
            d=copy.deepcopy(base);d['source_path']=f'A{i}';docs[d['source_path']]=d;candidates.append({**d,'score':i/300})
        selected=hybrid_rank('launch',candidates,docs,list(docs)[:250],999)
        self.assertEqual(len(selected),12)
        self.assertTrue(all(c['source_path'] in list(docs)[:250] for c in selected))

    def test_independent_lexical_hit_survives_vector_omission(self):
        docs=load_dataset(self.path)
        first,second=docs[:2]
        candidates=[{**first,'score':0.9}]
        lexical=[{**second,'score':0.001}]
        ranked=hybrid_rank('permission',candidates,{d['source_path']:d for d in docs},[d['source_path'] for d in docs],lexical_candidates=lexical)
        self.assertEqual({c['source_path'] for c in ranked},{first['source_path'],second['source_path']})
    def test_known_wrong_platform_and_unconfirmed_error_block_facts(self):
        doc=load_dataset(self.path)[0]
        self.assertFalse(applicability_status(doc['metadata'],{'system_area':'Moodle','exact_launch_error':True})['applicable'])
        self.assertFalse(applicability_status(doc['metadata'],{'system_area':'MCeLE'})['applicable'])
        self.assertTrue(applicability_status(doc['metadata'],{'system_area':'MCeLE','exact_launch_error':True})['applicable'])

class IncrementalEmbeddingTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_embedding_prevents_all_ingestion_writes(self):
        import os
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, patch
        from support import test_env
        import db
        import ingest
        manifest=ROOT/'knowledge/curated/manifest.json'
        config=SimpleNamespace(manifest=manifest,taxonomy=manifest.parent/'taxonomy.json')
        connection=MagicMock()
        connection.execute.return_value.fetchall.return_value=[]
        client=MagicMock()
        client.__aenter__.return_value=client
        client.post=AsyncMock(return_value=MagicMock(status_code=503))
        with patch.dict(os.environ,test_env()), patch.object(ingest,'validate_runtime',return_value=config), \
                patch.object(db,'init_pool'), patch.object(db,'close_pool'), \
                patch.object(db,'get_connection') as connect, patch('httpx.AsyncClient',return_value=client):
            connect.return_value.__enter__.return_value=connection
            with self.assertRaisesRegex(RuntimeError,'embedding request failed'):
                await ingest.ingest(manifest)
        client.post.assert_awaited_once()
        self.assertEqual(connect.call_count,1)
        self.assertEqual(connection.execute.call_count,1)
        self.assertTrue(connection.execute.call_args.args[0].startswith('SELECT '))

    async def test_unchanged_inputs_make_no_embedding_calls_but_changed_inputs_do(self):
        import os
        from unittest.mock import AsyncMock, Mock, patch
        from ingest import prepare_embeddings
        docs=load_dataset(ROOT/'knowledge/curated/manifest.json');model='nomic-embed-text'
        rows={d['source_path']:(d['source_path'],d['content_sha256'],{**d['metadata'],**embedding_fingerprint(d,model)},2 if d['retrieval_text'] else len(chunk_text(d['content']))) for d in docs}
        client=Mock();client.post=AsyncMock(return_value=Mock(status_code=200,json=lambda:{'embeddings':[[0.0]*768]}))
        with patch.dict(os.environ,{'OLLAMA_BASE_URL':'http://localhost:11434'}):
            prepared=await prepare_embeddings(docs,rows,model,client)
            self.assertTrue(all(v is None for v in prepared.values()));client.post.assert_not_awaited()
            changed=copy.deepcopy(docs[0]);changed['content']+='\nReviewed changed text.';changed['content_sha256']=hashlib.sha256(changed['content'].encode()).hexdigest()
            prepared=await prepare_embeddings([changed],rows,model,client)
            self.assertIsNotNone(prepared[changed['source_path']]);self.assertGreater(client.post.await_count,0)
    async def test_embedding_http_error_aborts_preparation(self):
        import os
        from unittest.mock import AsyncMock, Mock, patch
        from ingest import prepare_embeddings
        client=Mock();client.post=AsyncMock(return_value=Mock(status_code=503))
        with patch.dict(os.environ,{'OLLAMA_BASE_URL':'http://localhost:11434'}):
            with self.assertRaises(RuntimeError):
                await prepare_embeddings(load_dataset(ROOT/'knowledge/curated/manifest.json'),{},'nomic-embed-text',client)
