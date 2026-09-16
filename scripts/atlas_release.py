#!/usr/bin/env python3
"""Apply a verified demo release on Atlas; never targets existing application resources."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import time
import urllib.request

from release_guard import (PROJECT, ROOT, RUNTIME, SERVICES, CONTAINERS, NETWORK, VOLUME,
                           compose_args, reject_symlinks, render_and_validate, run, verify_release)


def http_json(url):
    with urllib.request.urlopen(url, timeout=8) as response:
        return json.load(response)


def original_health():
    with urllib.request.urlopen('http://127.0.0.1:8080/', timeout=8) as response:
        if response.status != 200:
            raise RuntimeError('Original frontend health failed')
    backend = http_json('http://127.0.0.1:8000/api/health')
    if backend.get('ok') is not True:
        raise RuntimeError('Original backend health failed')
    with urllib.request.urlopen('http://127.0.0.1:3000/api/public/health', timeout=8) as response:
        if response.status != 200:
            raise RuntimeError('Existing Langfuse health failed')
    return {'frontend': True, 'backend': True, 'langfuse': True, 'original_chunk_count': backend.get('chunk_count')}


def collision_check():
    all_names = set(run(['docker', 'ps', '-a', '--format', '{{.Names}}']).splitlines())
    ours = set(run(['docker', 'ps', '-a', '--filter', 'label=com.docker.compose.project='+PROJECT, '--format', '{{.Names}}']).splitlines())
    if not ours.issubset(set(CONTAINERS)):
        raise RuntimeError('Unexpected demo project containers or concurrent ingestion')
    for name in set(CONTAINERS) & all_names:
        item = json.loads(run(['docker', 'inspect', name]))[0]
        if item['Config'].get('Labels', {}).get('com.docker.compose.project') != PROJECT:
            raise RuntimeError('Container name belongs to another project')
        if name == PROJECT+'-db':
            if not any(m.get('Name') == VOLUME and m.get('Destination') == '/var/lib/postgresql/data' for m in item['Mounts']):
                raise RuntimeError('Demo database has an unexpected data mount')
    for kind, name in [('network', NETWORK), ('volume', VOLUME)]:
        known = set(run(['docker', kind, 'ls', '--format', '{{.Name}}']).splitlines())
        if name in known:
            item = json.loads(run(['docker', kind, 'inspect', name]))[0]
            if (item.get('Labels') or {}).get('com.docker.compose.project') != PROJECT:
                raise RuntimeError('Named resource belongs to another project')
    running = set(run(['docker', 'ps', '--format', '{{.Names}}']).splitlines())
    if PROJECT+'-frontend' not in running:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 8081))
    return sorted(set(CONTAINERS) & all_names)


def runtime_values():
    reject_symlinks(RUNTIME)
    if not RUNTIME.is_file() or RUNTIME.stat().st_mode & 0o077 or RUNTIME.parent.stat().st_mode & 0o077:
        raise RuntimeError('Provision the dedicated private runtime file on Atlas first')
    values = {}
    for line in RUNTIME.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        key, value = line.split('=', 1)
        if key in values:
            raise RuntimeError('Duplicate runtime setting')
        values[key] = value
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print('Plan: verified demo release only; --apply requires prior deployment approval.')
        return
    if sys.platform != 'linux' or socket.gethostname() != 'atlas':
        raise SystemExit('Apply must run on Atlas.')
    release = Path(__file__).resolve().parents[1]
    hashes = verify_release(release)
    values = runtime_values()
    sys.path.insert(0, str(release / 'backend'))
    from demo_config import validate_runtime
    validate_runtime(values)
    with (ROOT / 'deployment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        data = render_and_validate(release, RUNTIME, release.name)
        validate_runtime(data['services']['demo-backend']['environment'])
        previous = collision_check()
        if shutil.disk_usage(ROOT).free < 4 * 1024**3:
            raise RuntimeError('At least 4 GiB free disk required for the baseline')
        mem = next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
        if mem < 2_500_000:
            raise RuntimeError('Insufficient available RAM for conservative demo startup')
        before = original_health()
        inventory = {'project': PROJECT, 'release': str(release), 'release_id': release.name,
                     'containers': list(CONTAINERS), 'network': NETWORK, 'volume': VOLUME,
                     'image': PROJECT+'-backend:'+release.name, 'runtime_file': str(RUNTIME),
                     'local_frontend': 'http://127.0.0.1:8081', 'phase': 'deploying', 'original_before': before}
        inventory_path = ROOT / 'inventory.json'
        reject_symlinks(inventory_path)
        inventory_path.write_text(json.dumps(inventory, indent=2)+'\n')
        env = {k:v for k,v in os.environ.items() if k in ('PATH','HOME','DOCKER_HOST','DOCKER_CONTEXT','DOCKER_CONFIG')}
        env['DEMO_RELEASE_ID'] = release.name
        compose = compose_args(release, RUNTIME)
        try:
            # Build the new demo image before interrupting a previous demo release.
            print('Building isolated demo backend image...', flush=True)
            run(compose+['build', 'demo-backend'], env=env)
            stopping = [service for service, name in zip(SERVICES, CONTAINERS) if name in previous and service not in ('demo-db', 'demo-tunnel')]
            if stopping:
                run(compose+['--profile','public','stop',*stopping], env=env)
            print('Starting dedicated demo database and ingesting four approved articles...', flush=True)
            run(compose+['up','-d','demo-db'], env=env)
            run(compose+['run','--rm','demo-backend','python','ingest.py','--manifest','/knowledge/manifest.json'], env=env)
            run(compose+['up','-d','--no-deps','demo-backend','demo-frontend'], env=env)
            healthy = False
            for _ in range(30):
                try:
                    healthy = http_json('http://127.0.0.1:8081/api/health').get('ok') is True
                    if healthy: break
                except Exception:
                    pass
                time.sleep(2)
            if not healthy:
                raise RuntimeError('Demo failed readiness; public tunnel has not been started')
            print('Checking one demo conversation and Langfuse trace...', flush=True)
            run([sys.executable,str(release/'scripts/verify_deployment.py'),'--conversation'])
            # Preserve the existing demo Quick Tunnel process/URL on routine code updates.
            running_names=set(run(['docker','ps','--format','{{.Names}}']).splitlines())
            if PROJECT+'-tunnel' not in running_names:
                run(compose+['--profile','public','up','-d','--no-deps','demo-tunnel'], env=env)
            inventory['original_after'] = original_health()
            if inventory['original_after'] != before:
                raise RuntimeError('Original health/data snapshot changed; investigate without modifying original resources')
            inventory['phase'] = 'running'
            inventory_path.write_text(json.dumps(inventory,indent=2)+'\n')
            print('Isolated curated demo running; original health unchanged. Inventory saved. Verify the public URL separately.')
        except Exception:
            inventory['phase'] = 'needs-attention'
            inventory_path.write_text(json.dumps(inventory,indent=2)+'\n')
            raise


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        raise SystemExit('Demo deployment stopped: '+type(exc).__name__+'. Check demo-only configuration and inventory; command output was withheld to protect credentials.') from None
