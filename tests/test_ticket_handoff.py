"""Offline tests for neutral intake and conversation retrieval."""
import asyncio
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
def import_api():
    password = 'a' * 48  # Deliberately fake offline-only configuration.
    env = {'DEMO_INSTANCE_ID':'mcele-hackathon-demo','DEMO_DB_PASSWORD':password,
        'DATABASE_URL':f'postgresql://mcele_demo:{password}@demo-db:5432/mcele_demo',
        'OLLAMA_BASE_URL':'http://192.168.50.212:11434','OLLAMA_CHAT_MODEL':'qwen3:30b-a3b-instruct-2507-q4_K_M',
        'OLLAMA_VISION_MODEL':'qwen2.5vl:7b','OLLAMA_EMBED_MODEL':'nomic-embed-text',
        'LANGFUSE_HOST':'http://host.docker.internal:3000','LANGFUSE_PUBLIC_KEY':'offline-public',
        'LANGFUSE_SECRET_KEY':'offline-secret','LANGFUSE_PROJECT_ID':'offline-project',
        'LANGFUSE_TRACING_ENABLED':'false','DEMO_DATASET_MANIFEST':'/knowledge/manifest.json','TAXONOMY_PATH':'/knowledge/taxonomy.json'}
    with patch.dict(os.environ, env):
        import app
    return app


from demo_policy import PROFILES, resolve_context, resolve_access, TICKET_COURSES

class ContextTests(unittest.TestCase):
    def test_requested_choices_only(self):
        self.assertEqual(TICKET_COURSES, ('EPME4000','EPME5000','EPME3000','5500','6800','CYBERM0000','EWSPREREQ'))

    def test_unknown_mapping_can_be_clarified_without_granting_roles(self):
        context, conflict, _ = resolve_context('EPME4000', {}, None, 'My lesson will not launch', selected_system='Moodle')
        self.assertIsNone(conflict)
        self.assertEqual(context['system_area'], 'Moodle')
        self.assertEqual(resolve_access(PROFILES['student'], context, 'error').article_ids, ())

    def test_known_course_contradiction_denies_retrieval(self):
        context, conflict, _ = resolve_context('5500', {}, None, 'My lesson has an error', selected_system='MCeLE')
        self.assertTrue(conflict)
        self.assertEqual(resolve_access(PROFILES['student'], context, 'sts1.auth.ecuf.deas.mil refused to connect').article_ids, ())

    def test_system_change_is_a_memory_boundary(self):
        old, _, _ = resolve_context('6800', {}, None, 'My lesson will not launch', selected_system='MCeLE')
        new, conflict, changed = resolve_context('6800', old, '6800', 'My lesson will not launch', selected_system='Moodle')
        self.assertTrue(changed)
        self.assertIsNone(conflict)


class IntakeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.api = import_api()
        self.api.chat_lock = asyncio.Lock()

    def test_no_ticket_endpoint(self):
        self.assertNotIn('/api/ticket-draft', [r.path for r in self.api.app.routes])

    def test_category_is_optional_and_validated(self):
        from pydantic import ValidationError
        base = dict(session_id='s'*43, message='My course will not open')
        self.assertIsNone(self.api.ChatRequest(**base).issue_category)
        self.assertIsNone(self.api.ChatRequest(**base).course_id)
        with self.assertRaises(ValidationError):
            self.api.ChatRequest(**base, issue_category='Invented')
        with self.assertRaises(ValidationError):
            self.api.ChatRequest(**base, profile_id='ao')

    async def test_category_does_not_replace_report(self):
        request = self.api.ChatRequest(session_id='s'*43, message='My course will not open', issue_category='Account/Profile Issue')
        result = dict(answer='Article answer', sources=[], retrieved_count=0, trace_id=None, context={}, _context_changed=False, _image_text='')
        with patch.object(self.api, 'load_session', return_value={'id':'stored'}), patch.object(self.api, 'save_turn'), patch.object(self.api, 'answer_question', new_callable=AsyncMock, return_value=result) as answer:
            await self.api.chat(request)
            self.assertEqual(answer.call_args.args[0], 'My course will not open')
            self.assertIsNone(answer.call_args.kwargs['selected_course_id'])
            self.assertEqual(answer.call_args.kwargs['issue_category'], 'Account/Profile Issue')

    async def test_retrieval_embeds_full_history_before_search(self):
        import rag
        history = [{'role':'user','content':f'Report {i}: ' + 'x'*900} for i in range(10)]
        events=[]
        async def embed(query):
            events.append('embed')
            for item in history: self.assertIn(item['content'], query)
            self.assertIn('Current issue', query)
            self.assertIn('Screenshot evidence', query)
            return [0.1]*3
        def search(*args, **kwargs):
            events.append('search'); return []
        with patch.object(rag, 'embed_text', side_effect=embed), patch.object(rag, 'classify_question_bucket', return_value=[]), patch.object(rag, 'search_chunks', side_effect=search):
            await rag.retrieve_chunks('Current issue', history=history, image_context={'description':'Screenshot evidence'}, selected_bucket_id='test')
        self.assertEqual(events, ['embed','search'])

if __name__ == '__main__': unittest.main()
