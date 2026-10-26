"""Explicit approved curated allowlist; no directory crawling or Markdown import."""
import hashlib
import copy
from functools import lru_cache
import json
from pathlib import Path

from demo_config import ARTICLE_IDS, DATASET_ID

from article_registry import (ARTICLE_FILES, BUCKETS, ARTICLE_BUCKETS, DatasetError, read_json_file, read_registry)


def _load_dataset(manifest_path: Path) -> list[dict]:
    root = manifest_path.parent
    manifest = read_registry(manifest_path)
    documents = []
    expected = {"article_id", "title", "service_area", "allowed_roles", "course_scope", "course_ids", "content", "provenance", "synthetic", "redistribution"}
    for entry in manifest['articles']:
        rel, article_id = entry['file'], entry['article_id']
        article = read_json_file(root / rel, root)
        if hashlib.sha256((root / rel).read_bytes()).hexdigest() != entry['file_sha256']:
            raise DatasetError('Article differs from reviewed release hash')
        if not expected <= set(article) or set(article)-expected-{'retrieval_text','excluded_delivery_areas','required_error','section_conditions'}:
            raise DatasetError('Article fields do not match curated schema')
        if any(article[k] != entry[k] for k in ('article_id','allowed_roles','service_area','course_scope','course_ids')):
            raise DatasetError('Article differs from reviewed grants')
        if article['synthetic'] is not False or article['redistribution'] != 'pending-submission-review' or not isinstance(article['provenance'],dict) or article['provenance'].get('type') != 'adapted':
            raise DatasetError('Invalid reviewed source provenance')
        if article.get('required_error') != entry['applicability']['required_error'] or article.get('excluded_delivery_areas',[]) != entry['applicability']['excluded_delivery_areas']:
            raise DatasetError('Article applicability differs from registry')
        if not isinstance(article["title"], str) or not 1 <= len(article["title"]) <= 160:
            raise DatasetError("Invalid article title")
        content = article["content"]
        if not isinstance(content, str) or not 1 <= len(content) <= 8000:
            raise DatasetError("Invalid curated article content")
        if any(marker in content for marker in ("## Article record", "## Editorial and retrieval notes", "## Knowledge content")):
            raise DatasetError("Authoring sections cannot be embedded")
        from evidence_conditions import validate_metadata
        try:
            validate_metadata(content, article.get("section_conditions", []))
        except ValueError as exc:
            raise DatasetError(str(exc)) from exc
        retrieval_text = article.get("retrieval_text")
        if retrieval_text is not None and (not isinstance(retrieval_text, str) or not 1 <= len(retrieval_text) <= 1000):
            raise DatasetError("Invalid retrieval text")
        metadata = {k: v for k, v in article.items() if k not in {"content", "retrieval_text"}}
        metadata.update(dataset_id=DATASET_ID, clarification_bucket_id=entry['bucket_id'], bucket_label=manifest['buckets'][entry['bucket_id']], release_id=manifest['release_id'], release_sha256=manifest['release_sha256'], applicability=entry['applicability'])
        documents.append({"title": article["title"], "source_path": article_id,
                          "content": content, "metadata": metadata,
                          "retrieval_text": retrieval_text,
                          "content_sha256": hashlib.sha256(content.encode()).hexdigest()})
    return documents


@lru_cache(maxsize=4)
def _cached_dataset(path, manifest_stamp, article_stamps):
    return _load_dataset(Path(path))

@lru_cache(maxsize=4)
def _registry_files(path, stamp):
    return tuple(a['file'] for a in read_registry(Path(path))['articles'])

def load_dataset(manifest_path: Path) -> list[dict]:
    """Cache a validated snapshot; stat changes invalidate hashes before reuse."""
    path=Path(manifest_path)
    def stamp(p):
        st=p.stat()
        return (st.st_mtime_ns,st.st_ctime_ns,st.st_size,st.st_ino,p.is_symlink())
    manifest_stamp=stamp(path)
    files=_registry_files(str(path),manifest_stamp)
    article_stamps=tuple(stamp(path.parent / rel) for rel in files)
    return copy.deepcopy(_cached_dataset(str(path),manifest_stamp,article_stamps))


def validate_taxonomy(path: Path) -> dict[str, str]:
    data = read_json_file(path, path.parent)
    expected = {"clarification_buckets": {key:{"label":label} for key,label in BUCKETS.items()}, "articles": []}
    if data != expected:
        raise DatasetError("Curated taxonomy differs from the approved areas")
    return BUCKETS.copy()
