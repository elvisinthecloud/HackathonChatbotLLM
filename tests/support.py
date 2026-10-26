"""Shared offline configuration and canonical fixtures; no test cases or service calls."""
import copy
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]


def test_env():
    password = "a" * 48  # Deliberately fake; never used for a real connection.
    return {
        "DEMO_INSTANCE_ID": "mcele-hackathon-demo",
        "DEMO_DB_PASSWORD": password,
        "DATABASE_URL": f"postgresql://mcele_demo:{password}@demo-db:5432/mcele_demo",
        "OLLAMA_BASE_URL": "http://model-service:11434",
        "OLLAMA_CHAT_MODEL": "qwen3:30b-a3b-instruct-2507-q4_K_M",
        "OLLAMA_VISION_MODEL": "qwen2.5vl:7b",
        "OLLAMA_EMBED_MODEL": "nomic-embed-text",
        "LANGFUSE_HOST": "http://host.docker.internal:3000",
        "LANGFUSE_PUBLIC_KEY": "offline-public",
        "LANGFUSE_SECRET_KEY": "offline-secret",
        "LANGFUSE_PROJECT_ID": "offline-project",
        "LANGFUSE_TRACING_ENABLED": "false",
        "DEMO_DATASET_MANIFEST": "/knowledge/manifest.json",
        "DEMO_REGISTRY_PATH": str(ROOT / "knowledge/curated/manifest.json"),
        "TAXONOMY_PATH": "/knowledge/taxonomy.json",
    }


with patch.dict(os.environ, test_env()):
    import app as api

with patch.dict(os.environ, test_env()):
    import rag
    from demo_policy import PROFILES
from demo_dataset import load_dataset

MANIFEST = ROOT / 'knowledge/curated/manifest.json'


def chunk(article_id):
    documents = load_dataset(MANIFEST)
    document = next((d for d in documents if d['source_path'] == article_id), None)
    if document is None:
        raise AssertionError('Unknown reviewed article fixture: ' + article_id)
    return {**document, 'chunk_index': 0, 'score': 1.0,
            'article_metadata': copy.deepcopy(document['metadata'])}


def article(article_id):
    from article_registry import read_registry
    entry = next((a for a in read_registry(MANIFEST)['articles'] if a['article_id'] == article_id), None)
    if entry is None:
        raise AssertionError('Unknown reviewed article fixture: ' + article_id)
    return json.loads((MANIFEST.parent / entry['file']).read_text())


def make_session(profile, course=None, *, context=None, turns=None, version=0):
    return {'id': 'offline-' + profile, 'profile': copy.deepcopy(PROFILES[profile]),
            'selected_course_id': course, 'context': copy.deepcopy(context or {}),
            'version': version, 'revision': len(turns or []), 'turns': copy.deepcopy(turns or [])}


def launch_error():
    from article_registry import read_registry
    entry = next(a for a in read_registry(MANIFEST)['articles'] if a['article_id'] == 'MCELE-LAUNCH-001')
    return entry['applicability']['required_error']
