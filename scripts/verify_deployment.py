#!/usr/bin/env python3
"""Read health, or run a bounded curated conversation and inspect its dedicated trace."""
import argparse
import base64
import json
import re
import socket
import time
import urllib.request
from release_guard import require_deployment_host
from release_guard import ROOT, RUNTIME, reject_symlinks


def fetch(url, data=None, headers=None):
    req=urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,
                               headers={'Content-Type':'application/json',**(headers or {})})
    with urllib.request.urlopen(req,timeout=240 if data else 10) as response:
        return json.load(response)


def trace_headers():
    reject_symlinks(RUNTIME)
    env=dict(line.split('=',1) for line in RUNTIME.read_text().splitlines() if line and not line.startswith('#'))
    auth=base64.b64encode((env['LANGFUSE_PUBLIC_KEY']+':'+env['LANGFUSE_SECRET_KEY']).encode()).decode()
    return {'Authorization':'Basic '+auth}


def verify_trace(trace_id, role, article_id, source_only=True, allowed_article_ids=None,
                 require_allowed_set=False):
    expected={'rag_answer','access_filter','embed_text','article_candidate_search','vector_search','retrieval_route'}
    if source_only:
        expected.add('guided_response')
    else:
        expected.add('ollama_chat')
    headers=trace_headers()
    for _ in range(12):
        try:
            trace=fetch('http://127.0.0.1:3000/api/public/traces/'+trace_id,headers=headers)
            observed={o.get('name') for o in trace.get('observations',[])}
            metadata=trace.get('metadata') or {}
            allowed=metadata.get('allowed_article_ids')
            flexible = metadata.get('architecture') == 'flexible-grounded-rag'
            interpreted = metadata.get('architecture') == 'interpreted-evidence-dialogue'
            compact = metadata.get('architecture') == 'compact-evidence-dialogue'
            flexible = flexible or interpreted or compact
            if flexible:
                expected={'rag_answer','embed_text','article_candidate_search','support_draft','support_grounding_review'}
                if metadata.get('planner_version') == 2:
                    expected={'rag_answer','embed_text','article_candidate_search','support_planner'}
                if interpreted:
                    expected={'rag_answer','embed_text','article_candidate_search','support_interpretation','support_decision'}
                if compact:
                    expected={'rag_answer','embed_text','article_candidate_search','compact_interpretation','compact_reply'}
            access_ok = ((article_id in (allowed or []) if flexible else allowed == [article_id]) if allowed_article_ids is None else
                         (set(allowed or []) == set(allowed_article_ids) if require_allowed_set else
                          article_id in (allowed or []) and set(allowed or []).issubset(set(allowed_article_ids))))
            if (expected.issubset(observed) and 'curated-demo' in trace.get('tags',[]) and
                    metadata.get('role')==role and access_ok and
                    (not flexible or metadata.get('decision') in ('accepted','passages') and
                     article_id in metadata.get('cited_source_ids',[]))):
                return sorted(observed)
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError('Expected isolated curated trace not yet verified')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conversation',action='store_true')
    args=parser.parse_args()
    require_deployment_host()
    for port in (8000,8081):
        result=fetch(f'http://127.0.0.1:{port}/api/health')
        if result.get('ok') is not True:
            raise RuntimeError('Health failed')
        if port==8081 and result.get('dataset_id')!='mcele-curated-v1':
            raise RuntimeError('Wrong demo dataset')
    if not args.conversation:
        print('Original and curated demo health passed; no inference requested.')
        return
    session=fetch('http://127.0.0.1:8081/api/sessions',{'profile_id':'instructor','course_id':None})
    time.sleep(1.1)
    answer=fetch('http://127.0.0.1:8081/api/chat',{'session_id':session['session_id'],'message':'How do I copy a course in Moodle?','course_id':None})
    if not answer.get('sources') or any(s.get('source_path')!='MOODLE-COPY-002' for s in answer['sources']) or not answer.get('trace_id'):
        raise RuntimeError('Instructor permission/citation check failed')
    text=answer.get('answer','').lower()
    if not ('academics officer' in text or re.search(r'\bao\b',text)) or 'manage courses' in text or 'copy and view' in text:
        raise RuntimeError('Instructor answer must contain permission guidance without AO procedure')
    observed=verify_trace(answer['trace_id'],'Adjunct Faculty','MOODLE-COPY-002')
    report={'conversation':'passed','profile':'Instructor','citations':['MOODLE-COPY-002'],
            'trace_id':answer['trace_id'],'trace_observations':observed,'dataset_id':'mcele-curated-v1'}
    path=ROOT/'verification.json'
    reject_symlinks(path)
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    try: main()
    except Exception as exc:
        raise SystemExit('Demo verification failed: '+type(exc).__name__+'. No configuration values or response bodies printed.') from None
