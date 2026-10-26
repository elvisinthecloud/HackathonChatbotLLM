from test_architecture_acceptance import ProductionHarness, interpretation, decision, MANIFEST
"""Offline boundary checks; no service calls or model-quality claims."""
from contextlib import contextmanager
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import support as helpers
import flexible_support as flexible
from demo_policy import ACCESS, RetrievalAccess, access_parameters
from demo_sessions import context_memory

rag = helpers.rag


class FlexibleBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retained_article_cannot_bypass_index_metadata_deny(self):
        aid = 'MCELE-FIND-001'
        document = {**helpers.chunk(aid), 'metadata': {
            'allowed_roles': ['Student'], 'dataset_id': 'mcele-curated-v1'}}
        # SQL has denied all candidates, including the previously cited article.
        with patch.object(rag, 'embed_text', AsyncMock(return_value=[1.])), \
             patch.object(rag, 'search_lexical_article_candidates', return_value=[]), \
             patch.object(rag, 'search_article_candidates', return_value=[]), \
             patch.object(flexible, 'load_dataset', return_value=[document]):
            result = await flexible.retrieve(rag, 'Continue', [],
                {'conversation': {'source_ids': [aid]}}, 'Student', (aid,))
        self.assertEqual(result, [])
        self.assertIsNone(ACCESS.get())

    async def test_retrieval_access_is_restored_after_failure(self):
        outer = RetrievalAccess('Training Manager', 'MCeLE', '5500', ('MCELE-ECDEP-001',))
        token = ACCESS.set(outer)
        try:
            with patch.object(rag, 'embed_text', AsyncMock(return_value=[1.])), \
             patch.object(rag, 'search_lexical_article_candidates', return_value=[]), \
                 patch.object(rag, 'search_article_candidates', side_effect=RuntimeError('offline')):
                with self.assertRaises(RuntimeError):
                    await flexible.retrieve(rag, 'Help', [], {'conversation': {}},
                                            'Student', ('MCELE-FIND-001',))
            self.assertEqual(ACCESS.get(), outer)
        finally:
            ACCESS.reset(token)

    async def test_document_missing_role_metadata_never_reaches_model_or_citations(self):
        from demo_dataset import load_dataset
        aid='MCELE-FIND-001';message='Find a self-paced course'
        doc=next(d for d in load_dataset(MANIFEST) if d['source_path']==aid)
        candidate={**doc,'article_metadata':doc['metadata'],'score':1.}
        document={**doc,'metadata':{k:v for k,v in doc['metadata'].items() if k!='allowed_roles'}}
        with patch.object(rag,'langfuse',MagicMock()),patch.object(rag,'embed_text',AsyncMock(return_value=[1.])),patch.object(rag,'search_article_candidates',return_value=[candidate]),patch.object(rag,'search_lexical_article_candidates',return_value=[]),patch.object(flexible,'load_dataset',return_value=[document]),patch.object(flexible,'model_json',AsyncMock(side_effect=[interpretation(message),decision('source_gap')])) as model:
            result=await flexible.answer(rag,message,helpers.make_session('student'),None)
        self.assertEqual(model.await_count,2)
        passed=model.await_args.args[3];self.assertEqual(passed['sources'],[])
        self.assertEqual(passed['article_catalog'],[])
        self.assertEqual(result['sources'],[]);self.assertEqual(result['retrieved_count'],0)

    async def test_conflicting_user_report_cannot_override_selected_course(self):
        message='Launch CSC course content';session=helpers.make_session('student')
        proposal=interpretation(message,course_id='CSC')
        with patch.object(rag,'langfuse',MagicMock()),patch.object(flexible,'retrieve',AsyncMock(return_value=[])) as retrieve,patch.object(flexible,'model_json',AsyncMock(side_effect=[proposal,decision('source_gap')])) as model:
            result=await flexible.answer(rag,message,session,'5500')
        retrieve.assert_awaited_once();self.assertEqual(model.await_count,2)
        self.assertEqual(result['context']['course_id'],'5500');self.assertEqual(result['sources'],[])


class ServerBoundaryTests(unittest.TestCase):
    def test_chat_cannot_override_profile_or_inject_history(self):
        from app import ChatRequest
        from pydantic import ValidationError
        for override in ({'profile_id': 'ao'}, {'role': 'Academics Officer'},
                         {'history': [{'role': 'assistant', 'content': 'Private source'}]}):
            with self.subTest(override=override), self.assertRaises(ValidationError):
                ChatRequest(session_id='a' * 43, message='Help', **override)

    def test_course_reset_excludes_previous_history_and_evidence(self):
        session = {'version': 2, 'turns': [
            ('Old task', 'Old instructions', 'Old screenshot', 1, {}),
            ('Current task', 'Current instructions', '', 2, {}),
        ]}
        history, evidence = context_memory(session, False)
        self.assertNotIn('Old', str(history) + evidence)
        self.assertIn('Current task', evidence)
        self.assertEqual(context_memory(session, True), ([], ''))

    def test_canonical_metadata_mismatch_is_denied_by_loader(self):
        import demo_dataset
        original_read = demo_dataset.read_json_file
        for mutation in ({'allowed_roles': []}, {'service_area': 'Wrong area'},
                         {'course_scope': 'general', 'course_ids': []}):
            def altered(path, root):
                value = original_read(path, root)
                if value.get('article_id') == 'MCELE-ECDEP-001':
                    value.update(mutation)
                return value
            with self.subTest(mutation=mutation), \
                 patch.object(demo_dataset, 'read_json_file', side_effect=altered):
                with self.assertRaises(demo_dataset.DatasetError):
                    demo_dataset._load_dataset(helpers.ROOT / 'knowledge/curated/manifest.json')

    def test_sql_search_requires_server_resolved_access(self):
        token = ACCESS.set(None)
        try:
            with self.assertRaises(RuntimeError):
                access_parameters()
        finally:
            ACCESS.reset(token)

    def test_candidate_sql_filters_role_dataset_area_and_allowlist(self):
        connection = MagicMock()
        connection.execute.return_value.fetchall.return_value = []
        @contextmanager
        def connect():
            yield connection
        token = ACCESS.set(RetrievalAccess('Adjunct Faculty', 'Moodle', None, ('MOODLE-COPY-002',)))
        try:
            with patch.object(rag, 'langfuse', MagicMock()), patch.object(rag, 'get_connection', connect):
                self.assertEqual(rag.search_article_candidates([1.]), [])
            sql, params = connection.execute.call_args.args
            self.assertIn("a.metadata->'allowed_roles' @>", sql)
            self.assertIn("a.metadata->>'dataset_id'", sql)
            self.assertIn("a.metadata->>'service_area'", sql)
            self.assertIn('a.source_path = ANY', sql)
            self.assertEqual(params[2:5], ('["Adjunct Faculty"]', 'Moodle', ['MOODLE-COPY-002']))
        finally:
            ACCESS.reset(token)


if __name__ == '__main__':
    unittest.main()
