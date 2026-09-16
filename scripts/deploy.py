#!/usr/bin/env python3
"""Prepare a local release; stage/apply only after explicit deployment approval."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile

import sys
sys.dont_write_bytecode = True

from release_guard import ALLOWLIST, HOST, PROJECT, ROOT, release_id, render_and_validate, source_hashes

LOCAL = Path(__file__).resolve().parents[1]


def archive(hashes):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as tar:
        for rel in (*ALLOWLIST, 'release-hashes.json'):
            raw = json.dumps(hashes, sort_keys=True).encode() if rel == 'release-hashes.json' else (LOCAL / rel).read_bytes()
            if rel in hashes and hashlib.sha256(raw).hexdigest() != hashes[rel]:
                raise ValueError('Source changed while packaging; rerun plan')
            info = tarfile.TarInfo(rel)
            info.size = len(raw)
            info.mode = 0o644
            info.mtime = 0
            tar.addfile(info, io.BytesIO(raw))
    return output.getvalue()


def ssh_command(transport):
    if transport == 'tailscale':
        return ['tailscale', 'ssh', HOST]
    if transport == 'ssh':
        return ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=12', HOST]
    raise ValueError('Unsupported deployment transport')


def stage(blob, tag, transport='ssh'):
    # This bootstrap is carried as code, not a remote file; every archive member is
    # validated before any directory creation. No extractall or shell interpolation.
    remote_code = r'''
import hashlib,io,json,pathlib,sys,tarfile
root=pathlib.Path('/home/velvux/mcele-hackathon-demo')
expected=set(json.loads(sys.argv[2]))
tag=sys.argv[1]
assert len(tag)==16 and all(c in '0123456789abcdef' for c in tag)
assert not any(p.is_symlink() for p in (root,*root.parents))
raw=sys.stdin.buffer.read(5*1024*1024+1)
assert len(raw)<=5*1024*1024
files={}
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
 for member in tar.getmembers():
  assert member.isfile() and member.name in expected and member.name not in files
  assert 0<=member.size<=2*1024*1024
  files[member.name]=tar.extractfile(member).read()
assert set(files)==expected
hashes=json.loads(files.pop('release-hashes.json'))
assert set(hashes)==set(files)
assert all(hashlib.sha256(data).hexdigest()==hashes[name] for name,data in files.items())
digest=hashlib.sha256(''.join(f'{k}:{hashes[k]}\n' for k in sorted(hashes)).encode()).hexdigest()[:16]
assert digest==tag
marker=root/'.demo-root.json'
if root.exists():
 assert marker.is_file() and not marker.is_symlink() and json.loads(marker.read_text())=={'project':'mcele-hackathon-demo'}
else:
 root.mkdir(mode=0o700)
 marker.write_text(json.dumps({'project':'mcele-hackathon-demo'}))
release=root/'releases'/tag
assert not any(p.is_symlink() for p in (release,*release.parents))
files['release-hashes.json']=json.dumps(hashes,sort_keys=True).encode()
if release.exists():
 assert all(not (release/name).is_symlink() and (release/name).is_file() and (release/name).read_bytes()==data for name,data in files.items())
else:
 release.mkdir(parents=True,mode=0o700)
 for name,data in files.items():
  p=release/name
  p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f: f.write(data)
print('Staged verified demo release '+tag+'; no containers started.')
'''
    command = 'python3 -c ' + shlex.quote(remote_code) + ' ' + shlex.quote(tag) + ' ' + shlex.quote(json.dumps([*ALLOWLIST, 'release-hashes.json']))
    subprocess.run(ssh_command(transport) + [command], input=blob, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport', choices=('ssh', 'tailscale'), default='ssh',
                        help='Use standard SSH or tailnet-authorized Tailscale SSH')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--plan', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--stage', action='store_true', help='Upload approved files only; no services')
    mode.add_argument('--apply', action='store_true', help='Upload and deploy after approval and secret provisioning')
    args = parser.parse_args()
    hashes = source_hashes(LOCAL)
    tag = release_id(hashes)
    render_and_validate(LOCAL, LOCAL / 'config/runtime.env.example', tag, local=True)
    blob = archive(hashes)
    print(json.dumps({'project': PROJECT, 'host': HOST, 'destination': str(ROOT / 'releases' / tag),
                      'release_id': tag, 'allowlisted_files': len(hashes), 'archive_bytes': len(blob)}, indent=2))
    if not args.stage and not args.apply:
        print('Local plan only: no SSH, filesystem writes, containers, or secret reads.')
        return
    if os.environ.get('MCELE_DEMO_DEPLOY_APPROVED') != '1':
        raise SystemExit('Explicit first-deployment approval is required; then set MCELE_DEMO_DEPLOY_APPROVED=1.')
    stage(blob, tag, args.transport)
    if args.apply:
        command = 'python3 ' + shlex.quote(str(ROOT / 'releases' / tag / 'scripts/atlas_release.py')) + ' --apply'
        subprocess.run(ssh_command(args.transport) + [command], check=True)


if __name__ == '__main__':
    main()
