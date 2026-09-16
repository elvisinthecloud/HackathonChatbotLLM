#!/usr/bin/env python3
"""Remove only inventoried demo containers/network. Database volume is retained."""
import argparse
import fcntl
import json
from pathlib import Path
import socket
import sys
import sys
sys.dont_write_bytecode = True

from release_guard import ROOT, PROJECT, CONTAINERS, NETWORK, VOLUME, reject_symlinks, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not args.apply:
        print(json.dumps({'plan_only':True,'remove_containers':list(reversed(CONTAINERS)), 'remove_network':NETWORK,
                          'preserve_volume':VOLUME,'preserve_files':str(ROOT)},indent=2))
        return
    if sys.platform!='linux' or socket.gethostname()!='atlas':
        raise SystemExit('Rollback apply must run on Atlas.')
    reject_symlinks(ROOT)
    if json.loads((ROOT/'.demo-root.json').read_text()) != {'project':PROJECT}:
        raise RuntimeError('Missing demo root identity')
    reject_symlinks(ROOT/'inventory.json')
    inventory=json.loads((ROOT/'inventory.json').read_text())
    if inventory.get('project')!=PROJECT or inventory.get('containers')!=list(CONTAINERS) or inventory.get('network')!=NETWORK or inventory.get('volume')!=VOLUME:
        raise RuntimeError('Inventory differs from fixed demo resources')
    with (ROOT/'deployment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=set(run(['docker','ps','-a','--format','{{.Names}}']).splitlines())
        targets=[]
        for name in reversed(CONTAINERS):
            if name not in existing: continue
            obj=json.loads(run(['docker','inspect',name]))[0]
            if (obj['Config'].get('Labels') or {}).get('com.docker.compose.project')!=PROJECT:
                raise RuntimeError('Refusing container owned by another project')
            targets.append(obj['Id'])
        networks=set(run(['docker','network','ls','--format','{{.Name}}']).splitlines())
        network_id=None
        if NETWORK in networks:
            obj=json.loads(run(['docker','network','inspect',NETWORK]))[0]
            if (obj.get('Labels') or {}).get('com.docker.compose.project')!=PROJECT or not set(obj.get('Containers',{})).issubset(set(targets)):
                raise RuntimeError('Refusing network with another owner or unexpected attached container')
            network_id=obj['Id']
        for cid in targets: run(['docker','rm','--force',cid])
        if network_id: run(['docker','network','rm',network_id])
        inventory['phase']='stopped; volume retained'
        (ROOT/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
        print('Only inventoried demo containers/network removed. Demo volume, secrets, releases and images retained.')


if __name__=='__main__':
    main()
