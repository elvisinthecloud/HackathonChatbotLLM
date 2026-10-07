#!/usr/bin/env python3
"""Compare selected-source competition without changing chatbot access or storage.

Default: validate synthetic cases and inspect the current pure-Python router.
--embed-live: on the approved host only, rank the selected local source chunks
with the existing embedding model. No DB writes, ingestion, chat or deployment.
The exhaustive cosine diagnostic is not the production pgvector/API path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from access_support import ACCESS_BASELINE_ARTICLES
from demo_dataset import load_dataset
from demo_policy import PROFILES, clarification, resolve_access, resolve_context
from ingest import chunk_text

CASES = ROOT / "docs/retrieval-evaluation-cases.json"
MANIFEST = ROOT / "knowledge/curated/manifest.json"
MODEL = "nomic-embed-text"


def read_cases(path, documents):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "synthetic_retrieval_evaluation" or data.get("schema") != 1:
        raise ValueError("Unsupported evaluation schema")
    known = {d["source_path"] for d in documents}
    seen = set()
    for case in data["cases"]:
        if case["id"] in seen or case["profile_id"] not in PROFILES:
            raise ValueError("Duplicate case or unknown profile")
        seen.add(case["id"])
        if not case["turns"]:
            raise ValueError("Case must contain user turns")
        for turn in case["turns"]:
            action = turn["expected_action"]
            targets = turn["expected_article_ids"]
            if action not in {"source", "clarify", "deny"} or not turn["message"].strip():
                raise ValueError("Invalid turn expectation")
            if not isinstance(targets, list) or not set(targets).issubset(known):
                raise ValueError("Expectation references an unselected source")
            if (action == "source") != bool(targets):
                raise ValueError("Only source turns may specify target articles")
    return data["cases"]


def routing_audit(cases):
    """Exercise context/access resolution, without mocking successful retrieval.

    This audits routing only; procedure progress and response wording belong to
    the existing conversation tests. No assistant messages are fabricated.
    """
    rows = []
    for case in cases:
        previous = {}
        evidence = []
        selected = case.get("course_id")
        for index, turn in enumerate(case["turns"]):
            message = turn["message"]
            context, conflict, changed = resolve_context(selected, previous, selected, message)
            evidence = [message] if changed else [*evidence, message]
            access = resolve_access(PROFILES[case["profile_id"]], context, "\n".join(evidence))
            prompt = conflict or clarification(PROFILES[case["profile_id"]], context, "\n".join(evidence))
            action = "clarify" if prompt else "source" if access.article_ids else "deny"
            expected = turn["expected_action"]
            passed = action == expected and (expected != "source" or
                        bool(set(access.article_ids) & set(turn["expected_article_ids"])))
            rows.append({"case_id": case["id"], "turn": index + 1,
                         "message": message, "query": "\n".join(evidence),
                         "expected_action": expected,
                         "expected_article_ids": turn["expected_article_ids"],
                         "actual_action": action, "route_article_ids": list(access.article_ids),
                         "route_candidate_count": len(access.article_ids), "passed": passed,
                         "profile_id": case["profile_id"], "context": context})
            previous = context
    return rows


def diagnostic_eligible(document, row):
    """Explicit audience/system/course/evidence mask for ranking diagnostics.

    Unlike the production router, this deliberately does not infer article ID
    from intent. It exposes ranking competition only; its results never supply
    chatbot answers or change production permissions.
    """
    meta = document["metadata"]
    role = PROFILES[row["profile_id"]]["role"]
    context = row["context"]
    if role not in meta.get("allowed_roles", []):
        return False
    area = context.get("system_area")
    if area and meta.get("service_area") != area:
        return False
    if meta.get("course_scope") == "courses" and context.get("course_id") not in meta.get("course_ids", []):
        return False
    if meta.get("required_error") and meta["required_error"].casefold() not in row["query"].casefold():
        return False
    if area in meta.get("excluded_delivery_areas", []):
        return False
    return True


def source_chunks(document):
    # Match ingestion: AO routing text has a separate retrieval-only vector.
    bodies = [document["content"]] if document.get("retrieval_text") else chunk_text(document["content"])
    return [*bodies, *([document["retrieval_text"]] if document.get("retrieval_text") else [])]


def vector_key(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def valid_vector(vector):
    return (isinstance(vector, list) and len(vector) == 768 and
            all(type(v) in {int, float} and math.isfinite(v) for v in vector) and
            any(v != 0 for v in vector))


def cosine(left, right):
    if len(left) != len(right) or not left or not all(math.isfinite(v) for v in [*left, *right]):
        raise ValueError("Invalid ranking vector")
    left_norm, right_norm = math.hypot(*left), math.hypot(*right)
    if not left_norm or not right_norm:
        raise ValueError("Zero ranking vector")
    return math.fsum((a / left_norm) * (b / right_norm) for a, b in zip(left, right))


def rank_articles(query, documents, vectors):
    query_vector = vectors[vector_key(query)]
    ranked = []
    for document in documents:
        scores = [cosine(query_vector, vectors[vector_key(body)]) for body in source_chunks(document)]
        ranked.append({"article_id": document["source_path"], "score": max(scores)})
    return sorted(ranked, key=lambda item: (-item["score"], item["article_id"]))


def summarize_rankings(rows):
    result = {}
    for pool in ("access_six", "all_selected"):
        eligible = [row for row in rows if row["pool"] == pool and row["target_in_pool"]]
        result[pool] = {"scored_source_turns": len(eligible),
                        "top1_correct": sum(row["top1_correct"] for row in eligible),
                        "top3_contains_target": sum(row["top3_contains_target"] for row in eligible),
                        "wrong_top1": sum(not row["top1_correct"] for row in eligible)}
    return result


def score_rows(routes, documents, vectors):
    result = []
    for row in routes:
        allowed = [d for d in documents if diagnostic_eligible(d, row)]
        for pool, members in (("access_six", set(ACCESS_BASELINE_ARTICLES)),
                              ("all_selected", {d["source_path"] for d in documents})):
            candidates = [d for d in allowed if d["source_path"] in members]
            ranked = rank_articles(row["query"], candidates, vectors)
            targets = set(row["expected_article_ids"])
            target_in_pool = bool(targets & {d["source_path"] for d in candidates})
            result.append({"case_id": row["case_id"], "turn": row["turn"], "pool": pool,
                           "expected_action": row["expected_action"],
                           "eligible_article_count": len(candidates), "target_in_pool": target_in_pool,
                           "top_articles": [{**item, "score": round(item["score"], 6)} for item in ranked[:5]],
                           "top1_top2_margin": round(ranked[0]["score"] - ranked[1]["score"], 6) if len(ranked) > 1 else None,
                           "top1_correct": bool(ranked and ranked[0]["article_id"] in targets),
                           "top3_contains_target": bool(targets & {d["article_id"] for d in ranked[:3]})})
    return result


def live_vectors(texts):
    from release_guard import require_deployment_host
    require_deployment_host()
    # Preserve the configured model. Never print private endpoint/driver errors.
    if os.environ.get("OLLAMA_EMBED_MODEL") != MODEL:
        raise ValueError("Evaluation requires the unchanged approved embedding model")
    endpoint = os.environ["OLLAMA_BASE_URL"].rstrip("/") + "/api/embed"
    vectors = {}
    for item in texts:
        body = json.dumps({"model": MODEL, "input": item}).encode("utf-8")
        request = Request(endpoint, data=body, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=60) as response:
            data = json.load(response)
        vector = (data.get("embeddings") or [data.get("embedding")])[0]
        if not valid_vector(vector):
            raise ValueError("Expected a finite nonzero 768-dimensional embedding")
        vectors[vector_key(item)] = vector
        time.sleep(0.2)  # Small, sequential requests; no concurrent load test.
    return vectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--vectors", type=Path, help="Previously captured vectors from the approved embedding model")
    parser.add_argument("--embed-live", action="store_true", help="Only on the approved host with its private runtime environment")
    parser.add_argument("--cache-output", type=Path, help="Optional vector cache, outside tracked source")
    args = parser.parse_args()
    if args.vectors and args.embed_live or args.cache_output and not args.embed_live:
        parser.error("Choose cached or live vectors; cache-output requires embed-live")
    try:
        documents = load_dataset(MANIFEST)
        routes = routing_audit(read_cases(args.cases, documents))
        source_hashes = {d["source_path"]: vector_key(json.dumps(source_chunks(d))) for d in documents}
        report = {"type": "retrieval_evaluation", "synthetic_inputs": True,
                  "source_count": len(documents), "source_hashes": source_hashes,
                  "route_turns": len(routes), "route_passed": sum(row["passed"] for row in routes),
                  "single_candidate_source_routes": sum(row["actual_action"] == "source" and row["route_candidate_count"] == 1 for row in routes),
                  "vectors_verified": False, "live_embedding_model_verified": False,
                  "live_api_verified": False, "live_chat_model_verified": False,
                  "scope": "Router audit plus optional exhaustive cosine diagnostic; no production retrieval or answer generation",
                  "routing": routes}
        vectors = None
        if args.vectors:
            cache = json.loads(args.vectors.read_text(encoding="utf-8"))
            if cache.get("model") != MODEL or cache.get("source_hashes") != source_hashes:
                raise ValueError("Vector cache model or source hashes differ")
            vectors = cache["vectors"]
        elif args.embed_live:
            texts = list(dict.fromkeys([body for d in documents for body in source_chunks(d)] + [row["query"] for row in routes]))
            if len(texts) > 256:
                raise ValueError("Evaluation exceeds bounded embedding request count")
            vectors = live_vectors(texts)
            if args.cache_output:
                args.cache_output.write_text(json.dumps({"model": MODEL, "source_hashes": source_hashes, "vectors": vectors}) + "\n")
        if vectors is not None:
            needed = {vector_key(body) for d in documents for body in source_chunks(d)} | {vector_key(row["query"]) for row in routes}
            if not all(key in vectors and valid_vector(vectors[key]) for key in needed):
                raise ValueError("Vector cache is incomplete or invalid")
            scored = score_rows(routes, documents, vectors)
            report.update(vectors_verified=True, embedding_model=MODEL,
                          vector_origin="approved_host_live" if args.embed_live else "cache_with_unverified_provenance",
                          live_embedding_model_verified=bool(args.embed_live),
                          ranking=scored, ranking_summary=summarize_rankings(scored))
        encoded = json.dumps(report, indent=2) + "\n"
        if args.output:
            args.output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
    except Exception as exc:
        raise SystemExit("Retrieval evaluation failed (" + type(exc).__name__ + "); no connection details printed") from None


if __name__ == "__main__":
    main()
