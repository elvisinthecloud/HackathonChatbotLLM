"""Offline operational contracts: no network, inference, or deployment."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from support import api
import demo_sessions
import atlas_release
import release_guard


class OperationsTests(unittest.IsolatedAsyncioTestCase):
    async def test_tags_without_required_model_are_not_healthy(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (24,)
        with patch.object(api, 'get_connection') as connect, patch.object(api, 'check_ollama', AsyncMock(return_value=(True, ['unrelated:latest']))):
            connect.return_value.__enter__.return_value = conn
            result = await api.health()
        self.assertFalse(result['ok'])
        self.assertTrue(result['application_ready'])
        self.assertFalse(result['chat_model_available'])
        self.assertFalse(result['inference_verified'])

    async def test_code_readiness_does_not_call_model(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (24,)
        with patch.object(api, 'get_connection') as connect, patch.object(api, 'check_ollama', AsyncMock()) as model:
            connect.return_value.__enter__.return_value = conn
            self.assertEqual((await api.ready())['ready'], True)
            model.assert_not_called()

    async def test_session_conflict_returns_retry_without_success(self):
        api.chat_lock = asyncio.Lock()
        result = {'context': {}, '_context_changed': False, '_image_text': '', 'answer': 'unused', 'sources': [], 'retrieved_count': 0}
        with patch.object(api, 'load_session', return_value={}), patch.object(api, 'answer_question', AsyncMock(return_value=result)), patch.object(api, 'save_turn', side_effect=demo_sessions.SessionConflict):
            with self.assertRaises(api.HTTPException) as error:
                await api.chat(api.ChatRequest(session_id='s'*43, message='test'))
            self.assertEqual(error.exception.status_code, 409)

    def test_stale_revision_cannot_insert_turn(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        with patch.object(demo_sessions, 'get_connection') as connect:
            connect.return_value.__enter__.return_value = conn
            with self.assertRaises(demo_sessions.SessionConflict):
                demo_sessions.save_turn({'id': 'id', 'version': 1, 'revision': 4}, None, {}, False, 'q', '', False, {'answer': 'a'})
        self.assertEqual(conn.execute.call_count, 1)
        sql, values = conn.execute.call_args.args
        self.assertIn('revision=%s', sql)
        self.assertIn('expires_at>now()', sql)
        self.assertEqual(values[-1], 4)

    def test_code_deploy_checks_index_without_embedding(self):
        with patch.object(atlas_release, 'run') as run:
            atlas_release.prepare_index(['compose'], {}, reindex=False)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(commands), 2)
        self.assertIn('--check-only', commands[-1])
        self.assertFalse(any('stop' in cmd for cmd in commands))

    def test_stale_index_aborts_before_code_restart(self):
        with patch.object(atlas_release, 'run', side_effect=[None, RuntimeError('stale')]) as run:
            with self.assertRaises(RuntimeError):
                atlas_release.prepare_index(['compose'], {}, reindex=False)
        self.assertFalse(any('stop' in call.args[0] or 'demo-frontend' in call.args[0] for call in run.call_args_list))

    def test_packaging_uses_reviewed_article_registry_at_300_articles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            curated = root / 'knowledge/curated'
            curated.mkdir(parents=True)
            manifest = curated / 'manifest.json'
            manifest.write_text(json.dumps({'articles': [{'file': f'articles/article-{i}.json'} for i in range(300)]}))
            files = release_guard.release_files(root)
            self.assertEqual(sum(p.startswith('knowledge/curated/articles/') for p in files), 300)
            manifest.write_text(json.dumps({'articles': [{'file': '../../private.json'}]}))
            with self.assertRaises(ValueError):
                release_guard.release_files(root)
