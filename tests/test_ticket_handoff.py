"""Standalone ticket tests; no dependency on USB-lost test helpers or live services."""
import asyncio
import json
import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from demo_policy import PROFILES, resolve_context, resolve_access, TICKET_COURSES
from demo_tickets import relevant_reports, prepare_draft


def session(profile='student'):
    return {'id': 'offline-session', 'profile': PROFILES[profile], 'version': 2,
            'context': {}, 'selected_course_id': None, 'turns': [
        ('Old private report', 'Old answer', '', 1, {'course_id': '5500', 'system_area': 'MCeLE'}),
        ('Cannot open lesson', 'Try rebooting', '', 2, {'course_id': 'EPME4000', 'system_area': 'MCeLE'}),
        ('I already rebooted', 'Invented claim not user evidence', '', 2, {'course_id': 'EPME4000', 'system_area': 'MCeLE'}),
    ]}


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

    def test_reports_exclude_old_course_version_and_assistant_claims(self):
        reports = relevant_reports(session(), 'EPME4000', 'MCeLE')
        self.assertEqual(reports, ['Cannot open lesson', 'I already rebooted'])
        with self.assertRaises(ValueError): relevant_reports(session(), '5500', 'MCeLE')
        with self.assertRaises(ValueError): relevant_reports(session(), 'EPME4000', 'Moodle')

    def test_unlisted_course_and_unsent_issue(self):
        self.assertEqual(relevant_reports(session(), 'Course not listed', 'Moodle', 'My course is missing'), ['My course is missing'])


class DraftTests(unittest.IsolatedAsyncioTestCase):
    async def test_model_failure_falls_back_without_losing_report(self):
        settings = SimpleNamespace(chat_model='offline', ollama_base_url='http://offline.invalid', num_ctx=16384)
        client = AsyncMock(); client.__aenter__.return_value = client
        client.post.side_effect = ValueError('invalid model JSON')
        with patch('demo_tickets.httpx.AsyncClient', return_value=client):
            draft = await prepare_draft(session('instructor'), 'EPME4000', 'MCeLE', '', settings, MagicMock())
        self.assertEqual(draft['username'], 'username.instructor')
        self.assertEqual(draft['mode'], 'reported-text')
        self.assertTrue(draft['mock'])
        self.assertIn('I already rebooted', draft['description'])
        self.assertNotIn('Old private', draft['description'])
        self.assertNotIn('Try rebooting', draft['description'])

    async def test_ai_draft_preserves_server_controlled_fields(self):
        settings = SimpleNamespace(chat_model='offline', ollama_base_url='http://offline.invalid', num_ctx=16384)
        response = MagicMock()
        response.json.return_value = {'message': {'content': json.dumps({'summary': 'Lesson fails', 'description': 'User reports a failed lesson.', 'username': 'attacker'})}}
        client = AsyncMock(); client.__aenter__.return_value = client; client.post.return_value = response
        with patch('demo_tickets.httpx.AsyncClient', return_value=client):
            draft = await prepare_draft(session('ao'), 'EPME4000', 'MCeLE', '', settings, MagicMock())
        self.assertEqual(draft['mode'], 'ai-draft')
        self.assertEqual(draft['username'], 'username.ao')
        self.assertEqual(draft['course'], 'EPME4000')
        self.assertEqual(draft['issue_type'], 'MCeLE')


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


class EndpointTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.api = import_api()
        self.api.chat_lock = asyncio.Lock()

    def test_request_cannot_override_identity_or_use_invalid_site(self):
        from pydantic import ValidationError
        base = {'session_id':'s'*43,'course_id':'5500','system_area':'MCeLE'}
        for extra in ({'username':'attacker'}, {'profile_id':'ao'}, {'system_area':'Other'}, {'course_id':' '}):
            with self.subTest(extra=extra), self.assertRaises(ValidationError): self.api.TicketDraftRequest(**(base | extra))

    async def test_expired_session_cannot_prepare_draft(self):
        request = self.api.TicketDraftRequest(session_id='s'*43,course_id='5500',system_area='MCeLE')
        with patch.object(self.api,'load_session',side_effect=self.api.SessionMissing()), patch('demo_tickets.prepare_draft',new_callable=AsyncMock) as draft:
            with self.assertRaises(self.api.HTTPException) as error: await self.api.ticket_draft(request)
            self.assertEqual(error.exception.status_code,404);draft.assert_not_called()

    async def test_endpoint_uses_the_token_session(self):
        request = self.api.TicketDraftRequest(session_id='s'*43,course_id='EPME4000',system_area='MCeLE')
        stored = session('student')
        with patch.object(self.api,'load_session',return_value=stored), patch('demo_tickets.prepare_draft',new_callable=AsyncMock,return_value={'mock':True}) as draft:
            self.assertEqual(await self.api.ticket_draft(request), {'mock':True})
            self.assertIs(draft.call_args.args[0], stored)

if __name__ == '__main__': unittest.main()
