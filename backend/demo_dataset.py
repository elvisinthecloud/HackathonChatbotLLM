"""Explicit approved curated allowlist; no directory crawling or Markdown import."""
import hashlib
import json
from pathlib import Path

from demo_config import ARTICLE_IDS, DATASET_ID

ARTICLE_FILES = (
    "articles/mcele-course-launch-sts1-student.json",
    "articles/moodle-copy-permission-instructor.json",
    "articles/moodle-copy-course-ao.json",
    "articles/moodle-copy-stuck-ao.json",
    "articles/mcele-ecdep-request-tm.json",
    "articles/mcele-enrollment-report-tm.json",
    "articles/mcele-rrc-repeat-student.json",
    "articles/mcele-epme-eligibility-student.json",
)
BUCKETS = {"mcele-launch":"MCeLE course launch error", "moodle-copy":"Moodle course copying",
           "mcele-ecdep":"MCeLE ECDEP enrollment requests",
           "mcele-enrollment-report":"MCeLE enrollment reporting",
           "mcele-rrc":"MCeLE Reserve Retirement Credits",
           "mcele-epme":"MCeLE EPME eligibility and enrollment"}
ARTICLE_BUCKETS = dict(zip(ARTICLE_IDS, (
    "mcele-launch", "moodle-copy", "moodle-copy", "moodle-copy",
    "mcele-ecdep", "mcele-enrollment-report", "mcele-rrc", "mcele-epme",
)))


class DatasetError(ValueError):
    pass


def read_json_file(path: Path, root: Path) -> dict:
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
        raise DatasetError("Dataset symlinks are not allowed")
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise DatasetError("Dataset file must be inside the configured root")
    if path.stat().st_size > 32_768:
        raise DatasetError("Curated file exceeds size limit")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise DatasetError("Invalid dataset JSON") from exc
    if not isinstance(data, dict):
        raise DatasetError("Dataset record must be an object")
    return data


def load_dataset(manifest_path: Path) -> list[dict]:
    root = manifest_path.parent
    manifest = read_json_file(manifest_path, root)
    if manifest != {"dataset_id": DATASET_ID, "article_files": list(ARTICLE_FILES), "article_ids": list(ARTICLE_IDS)}:
        raise DatasetError("Curated manifest differs from the explicit file/ID allowlist")
    expected = {"article_id", "title", "service_area", "allowed_roles", "course_scope", "course_ids", "content", "provenance", "synthetic", "redistribution"}
    documents = []
    for rel, article_id in zip(ARTICLE_FILES, ARTICLE_IDS):
        article = read_json_file(root / rel, root)
        from demo_policy import ARTICLE_POLICY
        role, area, scope, courses = ARTICLE_POLICY[article_id]
        extras = set()
        if article_id == "MCELE-LAUNCH-001":
            extras.update({"excluded_delivery_areas", "required_error"})
        if article_id in {"MOODLE-COPY-001", "MOODLE-COPY-003"}:
            extras.add("retrieval_text")
        if set(article) != expected | extras:
            raise DatasetError("Article fields do not match curated schema")
        if not (article["article_id"] == article_id and article["allowed_roles"] == [role]
                and article["synthetic"] is False and article["service_area"] == area
                and article["course_scope"] == scope and article["course_ids"] == list(courses)
                and article["redistribution"] == "pending-submission-review"
                and isinstance(article["provenance"], dict) and article["provenance"].get("type") == "adapted"):
            raise DatasetError("Curated article differs from its explicit access/scope policy")
        if article_id == "MCELE-LAUNCH-001" and (article["excluded_delivery_areas"] != ["Moodle"] or article["required_error"] != "sts1.auth.ecuf.deas.mil refused to connect"):
            raise DatasetError("Student article requires the approved error and Moodle exclusion")
        if not isinstance(article["title"], str) or not 1 <= len(article["title"]) <= 160:
            raise DatasetError("Invalid article title")
        content = article["content"]
        if not isinstance(content, str) or not 1 <= len(content) <= 8000:
            raise DatasetError("Invalid curated article content")
        if any(marker in content for marker in ("## Article record", "## Editorial and retrieval notes", "## Knowledge content")):
            raise DatasetError("Authoring sections cannot be embedded")
        retrieval_text = article.get("retrieval_text")
        if retrieval_text is not None and (not isinstance(retrieval_text, str) or not 1 <= len(retrieval_text) <= 1000):
            raise DatasetError("Invalid retrieval text")
        metadata = {k: v for k, v in article.items() if k not in {"content", "retrieval_text"}}
        metadata.update(dataset_id=DATASET_ID, clarification_bucket_id=ARTICLE_BUCKETS[article_id], bucket_label=BUCKETS[ARTICLE_BUCKETS[article_id]])
        documents.append({"title": article["title"], "source_path": article_id,
                          "content": content, "metadata": metadata,
                          "retrieval_text": retrieval_text,
                          "content_sha256": hashlib.sha256(content.encode()).hexdigest()})
    return documents


def validate_taxonomy(path: Path) -> dict[str, str]:
    data = read_json_file(path, path.parent)
    expected = {"clarification_buckets": {key:{"label":label} for key,label in BUCKETS.items()}, "articles": []}
    if data != expected:
        raise DatasetError("Curated taxonomy differs from the approved areas")
    return BUCKETS.copy()
