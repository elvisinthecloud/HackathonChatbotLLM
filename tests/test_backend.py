"""Recovered offline test bootstrap used by grounding and session tests.

The former full backend test module was lost with the USB workspace. This file
restores only the exact fake environment and patched app import preserved in
recovery/partial-documents/test_backend.partial.txt; it does not claim to
reconstruct the missing test cases.
"""
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
        "OLLAMA_BASE_URL": "http://192.168.50.212:11434",
        "OLLAMA_CHAT_MODEL": "qwen3:30b-a3b-instruct-2507-q4_K_M",
        "OLLAMA_VISION_MODEL": "qwen2.5vl:7b",
        "OLLAMA_EMBED_MODEL": "nomic-embed-text",
        "LANGFUSE_HOST": "http://host.docker.internal:3000",
        "LANGFUSE_PUBLIC_KEY": "offline-public",
        "LANGFUSE_SECRET_KEY": "offline-secret",
        "LANGFUSE_PROJECT_ID": "offline-project",
        "LANGFUSE_TRACING_ENABLED": "false",
        "DEMO_DATASET_MANIFEST": "/knowledge/manifest.json",
        "TAXONOMY_PATH": "/knowledge/taxonomy.json",
    }


with patch.dict(os.environ, test_env()):
    import app as api
