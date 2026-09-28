#!/usr/bin/env python3
"""Interactively provision dedicated demo keys on the deployment host after deployment approval."""
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sys

from release_guard import require_deployment_host
from release_guard import ROOT, RUNTIME, PROJECT, reject_symlinks


def main():
    if sys.platform != 'linux' or not sys.stdin.isatty():
        raise SystemExit('Run interactively on the deployment host with ssh -t, after staging the approved release.')
    require_deployment_host()
    reject_symlinks(ROOT)
    if json.loads((ROOT / '.demo-root.json').read_text()) != {'project': PROJECT}:
        raise SystemExit('Stage the approved demo release first.')
    reject_symlinks(RUNTIME)
    if RUNTIME.exists():
        raise SystemExit('Demo runtime already exists; refusing overwrite.')
    print('Use a separate Langfuse project named: MCeLE Hackathon Demo. Do not paste keys into chat.')
    project = input('Demo Langfuse project ID (not a secret): ').strip()
    public = getpass.getpass('Demo Langfuse public key (hidden): ').strip()
    secret = getpass.getpass('Demo Langfuse secret key (hidden): ').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,100}', project) or not re.fullmatch(r'pk-lf-[A-Za-z0-9_-]+', public) or not re.fullmatch(r'sk-lf-[A-Za-z0-9_-]+', secret):
        raise SystemExit('Unexpected demo project/key format. No configuration written.')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
    from demo_config import validate_ollama_url
    ollama_url = validate_ollama_url(getpass.getpass('Existing Ollama URL (hidden): ').strip())
    password = secrets.token_hex(24)
    values = {'DEMO_INSTANCE_ID': PROJECT, 'DEMO_DB_PASSWORD': password,
              'DATABASE_URL': f'postgresql://mcele_demo:{password}@demo-db:5432/mcele_demo',
              'OLLAMA_BASE_URL': ollama_url,
              'OLLAMA_CHAT_MODEL': 'qwen3:30b-a3b-instruct-2507-q4_K_M', 'OLLAMA_VISION_MODEL': 'qwen2.5vl:7b',
              'OLLAMA_EMBED_MODEL': 'nomic-embed-text', 'TAXONOMY_PATH': '/knowledge/taxonomy.json',
              'DEMO_DATASET_MANIFEST': '/knowledge/manifest.json', 'LANGFUSE_HOST': 'http://host.docker.internal:3000',
              'LANGFUSE_PROJECT_ID': project, 'LANGFUSE_PUBLIC_KEY': public, 'LANGFUSE_SECRET_KEY': secret}
    previous = os.umask(0o077)
    try:
        RUNTIME.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(RUNTIME.parent, 0o700)
        fd = os.open(RUNTIME, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(''.join(f'{k}={v}\n' for k,v in values.items()))
    finally:
        os.umask(previous)
    print('Dedicated demo runtime saved on the deployment host with mode 0600; no credentials printed.')


if __name__ == '__main__':
    main()
