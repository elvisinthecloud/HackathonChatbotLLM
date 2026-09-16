"""Fail-closed configuration for the isolated Atlas baseline.

This module uses only the standard library so validation can run before dependencies
or network connections are initialized. Error messages never include config values.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit
import os
import re

INSTANCE_ID = "mcele-hackathon-demo"
DATASET_ID = "mcele-curated-v1"
DATABASE_NAME = "mcele_demo"
ARTICLE_IDS = (
    "MCELE-LAUNCH-001",
    "MOODLE-COPY-002",
    "MOODLE-COPY-001",
    "MOODLE-COPY-003",
    "MCELE-ECDEP-001",
    "MCELE-ENROLLMENT-REPORT-001",
    "MCELE-RRC-001",
    "MCELE-EPME-001",
)


class DemoConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DemoConfig:
    database_url: str = field(repr=False)
    manifest: Path
    taxonomy: Path


def validate_runtime(env: Mapping[str, str] | None = None) -> DemoConfig:
    env = os.environ if env is None else env
    required = {
        "DEMO_INSTANCE_ID": INSTANCE_ID,
        "OLLAMA_BASE_URL": "http://192.168.50.212:11434",
        "OLLAMA_CHAT_MODEL": "qwen3:30b-a3b-instruct-2507-q4_K_M",
        "OLLAMA_VISION_MODEL": "qwen2.5vl:7b",
        "OLLAMA_EMBED_MODEL": "nomic-embed-text",
        "LANGFUSE_HOST": "http://host.docker.internal:3000",
        "DEMO_DATASET_MANIFEST": "/knowledge/manifest.json",
        "TAXONOMY_PATH": "/knowledge/taxonomy.json",
    }
    for key, expected in required.items():
        if env.get(key) != expected:
            raise DemoConfigurationError(f"Missing or unexpected demo setting: {key}")
    for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        value = env.get(key, "")
        if not value or any(c.isspace() for c in value) or value.upper().startswith(("REPLACE", "CHANGE", "YOUR_")):
            raise DemoConfigurationError(f"Dedicated demo credential required: {key}")
    project_id = env.get("LANGFUSE_PROJECT_ID", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", project_id):
        raise DemoConfigurationError("Expected demo LANGFUSE_PROJECT_ID is required")
    password = env.get("DEMO_DB_PASSWORD", "")
    if not re.fullmatch(r"[a-f0-9]{32,128}", password):
        raise DemoConfigurationError("DEMO_DB_PASSWORD must be a generated hexadecimal secret")
    dsn = env.get("DATABASE_URL", "")
    try:
        parsed = urlsplit(dsn)
        valid = (
            parsed.scheme == "postgresql" and parsed.hostname == "demo-db"
            and parsed.port == 5432 and parsed.path == "/mcele_demo"
            and parsed.username == "mcele_demo" and parsed.password == password
            and not parsed.query and not parsed.fragment
            and dsn == f"postgresql://mcele_demo:{password}@demo-db:5432/mcele_demo"
        )
    except ValueError:
        valid = False
    if not valid:
        raise DemoConfigurationError("DATABASE_URL must target only the dedicated demo database")
    return DemoConfig(dsn, Path(required["DEMO_DATASET_MANIFEST"]), Path(required["TAXONOMY_PATH"]))
