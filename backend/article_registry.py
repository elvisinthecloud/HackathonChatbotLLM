"""Reviewed release registry. Runtime grants are derived, never inferred from roles."""
import hashlib
import json
import os
from pathlib import Path

DATASET_ID = 'mcele-curated-v1'
ROLES = {'Student','Adjunct Faculty','Academics Officer','Training Manager','Regional Director'}
DEFAULT_MANIFEST = Path(os.environ.get('DEMO_REGISTRY_PATH', os.environ.get('DEMO_DATASET_MANIFEST', Path(__file__).resolve().parent.parent / 'knowledge/curated/manifest.json')))

class DatasetError(ValueError):
    pass

def read_json_file(path, root):
    path, root = Path(path), Path(root)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
        raise DatasetError('Dataset symlinks are not allowed')
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise DatasetError('Dataset file must be inside the configured root')
    if path.stat().st_size > 1048576:
        raise DatasetError('Curated file exceeds size limit')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise DatasetError('Invalid dataset JSON') from exc
    if not isinstance(data,dict): raise DatasetError('Dataset record must be an object')
    return data

def read_registry(path=DEFAULT_MANIFEST):
    path=Path(path)
    m=read_json_file(path,path.parent)
    if set(m)!={'schema_version','dataset_id','release_id','buckets','articles'} or m['schema_version']!=1 or m['dataset_id']!=DATASET_ID:
        raise DatasetError('Invalid reviewed registry schema')
    if not isinstance(m['release_id'],str) or not m['release_id'] or not isinstance(m['buckets'],dict) or not isinstance(m['articles'],list) or not 1<=len(m['articles'])<=1000:
        raise DatasetError('Invalid registry release')
    ids=set(); files=set()
    for a in m['articles']:
        if not isinstance(a,dict) or set(a)!={'article_id','file','file_sha256','allowed_roles','service_area','course_scope','course_ids','bucket_id','applicability'}:
            raise DatasetError('Invalid registry article fields')
        roles=a['allowed_roles']; courses=a['course_ids']; cond=a['applicability']
        if not isinstance(a['article_id'],str) or not a['article_id'] or a['article_id'] in ids or not isinstance(a['file'],str) or a['file'] in files:
            raise DatasetError('Duplicate or invalid article identity')
        ids.add(a['article_id']); files.add(a['file'])
        if not isinstance(roles,list) or not roles or any(not isinstance(r,str) or r not in ROLES for r in roles) or len(set(roles))!=len(roles):
            raise DatasetError('Explicit valid role grants required')
        if a['service_area'] not in {'MCeLE','Moodle'} or a['course_scope'] not in {'general','courses'} or not isinstance(courses,list) or any(not isinstance(c,str) or not c for c in courses) or (a['course_scope']=='courses')!=bool(courses):
            raise DatasetError('Invalid article scope')
        if a['bucket_id'] not in m['buckets'] or not isinstance(a['file_sha256'],str) or len(a['file_sha256'])!=64:
            raise DatasetError('Invalid article release record')
        if not isinstance(cond,dict) or set(cond)!={'course_ids','excluded_course_ids','required_error','excluded_delivery_areas','access_method'} or cond['course_ids']!=courses:
            raise DatasetError('Invalid applicability conditions')
        for key in ('excluded_course_ids','excluded_delivery_areas'):
            if not isinstance(cond[key],list) or any(not isinstance(v,str) for v in cond[key]): raise DatasetError('Invalid applicability values')
        if cond['access_method'] not in (None,'app','browser') or (cond['required_error'] is not None and (not isinstance(cond['required_error'],str) or not cond['required_error'])):
            raise DatasetError('Invalid applicability requirement')
    m['release_sha256']=hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return m

REGISTRY = read_registry()
ARTICLE_IDS = tuple(a['article_id'] for a in REGISTRY['articles'])
ARTICLE_FILES = tuple(a['file'] for a in REGISTRY['articles'])
BUCKETS = REGISTRY['buckets']
ARTICLE_BUCKETS = {a['article_id']:a['bucket_id'] for a in REGISTRY['articles']}
ARTICLE_POLICY = {a['article_id']: (a['allowed_roles'][0] if len(a['allowed_roles'])==1 else tuple(a['allowed_roles']),a['service_area'],a['course_scope'],tuple(a['course_ids'])) for a in REGISTRY['articles']}
