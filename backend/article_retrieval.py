"""Bounded hybrid candidates and exact canonical evidence; no model authority."""
import re
from article_registry import REGISTRY

MAX_CANDIDATES = 12

def authorized_ids(role):
    return tuple(a['article_id'] for a in REGISTRY['articles'] if role in a['allowed_roles'])

def applicability_status(metadata, context):
    c=metadata.get('applicability')
    if not isinstance(c,dict): return {'applicable':False,'missing':['reviewed applicability'],'conflicts':[]}
    missing=[]; conflicts=[]
    course=context.get('course_id')
    if c['course_ids']:
        if not course: missing.append('course_id')
        elif course not in c['course_ids']: conflicts.append('course_id')
    if course in c['excluded_course_ids']: conflicts.append('course_id')
    if context.get('system_area') in c['excluded_delivery_areas']: conflicts.append('system_area')
    if context.get('system_area') and context['system_area'] != metadata.get('service_area'): conflicts.append('system_area')
    if c['required_error']:
        normalized=lambda value: ' '.join(str(value or '').casefold().split())
        confirmed=normalized(context.get('confirmed_error_text'))==normalized(c['required_error'])
        confirmed=confirmed or (c['required_error']=='sts1.auth.ecuf.deas.mil refused to connect' and context.get('exact_launch_error') is True)
        if not confirmed: missing.append('exact_launch_error')
    if c['access_method']:
        if not context.get('access_method'): missing.append('access_method')
        elif context['access_method']!=c['access_method']: conflicts.append('access_method')
    return {'applicable':not missing and not conflicts,'missing':missing,'conflicts':conflicts}

def verify_candidate(candidate, document):
    return (candidate.get('content_sha256')==document['content_sha256']
            and candidate.get('article_metadata',candidate.get('metadata',{})).get('release_sha256')==document['metadata']['release_sha256'])

def hybrid_rank(query, candidates, documents, allowed, limit=MAX_CANDIDATES, lexical_candidates=()):
    """Reciprocal-rank fusion of bounded vector hits and authorized lexical search.

    Lexical candidates can only hydrate when a verified indexed candidate exists;
    callers supply independently retrieved lexical hits via lexical_candidates.
    """
    allowed=set(allowed)
    vector_ids={c['source_path'] for c in candidates}
    lexical_ids=[c['source_path'] for c in lexical_candidates]
    candidates=[*candidates,*lexical_candidates]
    valid={c['source_path']:c for c in reversed(candidates) if c['source_path'] in allowed and c['source_path'] in documents and verify_candidate(c,documents[c['source_path']])}
    tokens=set(re.findall(r'\w+',query.casefold()))
    scores={aid:0.0 for aid in valid}
    vector=sorted((aid for aid in valid if aid in vector_ids),key=lambda aid:valid[aid].get('score',0),reverse=True)
    lexical=sorted(valid,key=lambda aid:sum((documents[aid]['title']+' '+documents[aid]['content']+' '+(documents[aid].get('retrieval_text') or '')).casefold().count(t) for t in tokens if len(t)>2),reverse=True)
    if lexical_ids: lexical=list(dict.fromkeys(aid for aid in lexical_ids if aid in valid))
    for ranking in (vector,lexical):
        for i,aid in enumerate(ranking): scores[aid]+=1/(60+i+1)
    return [{**valid[aid],'hybrid_score':scores[aid]} for aid in sorted(scores,key=lambda aid:scores[aid],reverse=True)[:min(MAX_CANDIDATES,max(0,limit))]]

def canonical_units(document):
    """Paragraph units carry exact offsets; lists remain intact with qualifiers."""
    text=document['content']; result=[]
    for n,match in enumerate(re.finditer(r'\S[\s\S]*?(?=\n\s*\n|\Z)',text)):
        start,end=match.span()
        result.append({'evidence_id':document['source_path']+':'+str(n),'article_id':document['source_path'],'start':start,'end':end,'text':text[start:end],'content_sha256':document['content_sha256'],'applicability':document['metadata']['applicability']})
    return result
