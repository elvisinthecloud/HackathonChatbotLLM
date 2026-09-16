"""Shared standard-library deployment guards; no network or writes on import."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

PROJECT = "mcele-hackathon-demo"
HOST = "velvux@100.98.232.101"
ROOT = Path("/home/velvux/mcele-hackathon-demo")
RUNTIME = Path("/home/velvux/.config/mcele-hackathon-demo/runtime.env")
SERVICES = ("demo-db", "demo-backend", "demo-frontend", "demo-tunnel")
CONTAINERS = tuple(PROJECT + "-" + name for name in ("db", "backend", "frontend", "tunnel"))
NETWORK = PROJECT + "-network"
VOLUME = PROJECT + "-postgres-data"
ALLOWLIST = (
    "compose.demo.yml", "backend/Dockerfile", "backend/.dockerignore",
    "backend/app.py", "backend/db.py", "backend/ingest.py", "backend/demo_config.py", "backend/demo_dataset.py", "backend/demo_policy.py", "backend/demo_sessions.py",
    "backend/prompts.py", "backend/rag.py", "backend/requirements.txt", "backend/requirements.lock", "backend/text_utils.py",
    "frontend/index.html", "frontend/chat-widget.css", "frontend/chat-widget.js", "frontend/nginx.conf",
    "database/schema.sql", "knowledge/curated/articles/mcele-course-launch-sts1-student.json",
    "knowledge/curated/articles/moodle-copy-permission-instructor.json", "knowledge/curated/articles/moodle-copy-course-ao.json",
    "knowledge/curated/articles/moodle-copy-stuck-ao.json", "knowledge/curated/articles/mcele-ecdep-request-tm.json",
    "knowledge/curated/articles/mcele-enrollment-report-tm.json", "knowledge/curated/articles/mcele-rrc-repeat-student.json",
    "knowledge/curated/manifest.json", "knowledge/curated/taxonomy.json",
    "scripts/deploy.py", "scripts/configure_runtime.py", "scripts/rollback.py", "scripts/release_guard.py",
    "scripts/atlas_release.py", "scripts/verify_deployment.py", "scripts/verify_scenarios.py", "verification/synthetic-sts1.png",
)


def reject_symlinks(path: Path) -> None:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Symlinks are forbidden in deployment paths")


def release_id(hashes: dict) -> str:
    return hashlib.sha256("".join(f"{p}:{hashes[p]}\n" for p in sorted(hashes)).encode()).hexdigest()[:16]


def source_hashes(local: Path) -> dict:
    result = {}
    for rel in ALLOWLIST:
        p = local / rel
        reject_symlinks(p)
        if not p.is_file():
            raise ValueError("Missing allowlisted source: " + rel)
        raw = p.read_bytes()
        if re.search(rb"(?:sk-lf-|pk-lf-)[A-Za-z0-9_-]{12,}|postgresql://\w+:[a-f0-9]{32,}@", raw):
            raise ValueError("Credential pattern found in release source: " + rel)
        result[rel] = hashlib.sha256(raw).hexdigest()
    return result


def run(args, *, env=None, input=None):
    result = subprocess.run(args, env=env, input=input, capture_output=True, text=True)
    if result.returncode:
        # Avoid echoing environment-resolved Compose or driver errors.
        raise RuntimeError("Deployment command failed: " + Path(args[0]).name + " (output withheld)")
    return result.stdout


def compose_args(release: Path, env_file: Path) -> list[str]:
    return ["docker", "compose", "-f", str(release / "compose.demo.yml"), "--project-directory", str(release),
            "--env-file", str(env_file), "-p", PROJECT]


def render_and_validate(release: Path, env_file: Path, tag: str, *, local=False) -> dict:
    # Do not inherit Compose overrides or secret-variable substitutions from the shell.
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG")}
    env["DEMO_RELEASE_ID"] = tag
    command = compose_args(release, env_file) + ["--profile", "public", "config", "--format", "json"]
    if local:
        env["DEMO_RUNTIME_FILE"] = str(env_file)
    data = json.loads(run(command, env=env))
    if data.get("name") != PROJECT or set(data["services"]) != set(SERVICES):
        raise ValueError("Unexpected Compose project/services")
    expected_mounts = {
        "demo-db": {(VOLUME, "/var/lib/postgresql/data", False, "volume"),
                    (str(release / "database/schema.sql"), "/docker-entrypoint-initdb.d/001-schema.sql", True, "bind")},
        "demo-backend": {(str(release / "knowledge/curated"), "/knowledge", True, "bind")},
        "demo-frontend": {(str(release / "frontend"), "/usr/share/nginx/html", True, "bind"),
                          (str(release / "frontend/nginx.conf"), "/etc/nginx/conf.d/default.conf", True, "bind")},
        "demo-tunnel": set(),
    }
    for service, container in zip(SERVICES, CONTAINERS):
        cfg = data["services"][service]
        if cfg.get("container_name") != container or set(cfg.get("networks", {})) != {NETWORK}:
            raise ValueError("Unexpected container/network")
        if cfg.get("privileged") or cfg.get("network_mode") or cfg.get("pid") or cfg.get("devices"):
            raise ValueError("Host access configuration is forbidden")
        mounts = {(m["source"], m["target"], m.get("read_only", False), m["type"]) for m in cfg.get("volumes", [])}
        if mounts != expected_mounts[service]:
            raise ValueError("Unexpected mount set")
        budgets = {"demo-db": (0.75, 768), "demo-backend": (1.5, 1024), "demo-frontend": (0.25, 256), "demo-tunnel": (0.25, 256)}
        cpu, mib = budgets[service]
        if float(cfg.get("cpus", 0)) != cpu or int(cfg.get("mem_limit", 0)) != mib * 1024 * 1024:
            raise ValueError("Resource limits differ from the approved baseline")
        images = {"demo-db": "pgvector/pgvector:pg16", "demo-frontend": "nginx:alpine",
                  "demo-tunnel": "cloudflare/cloudflared:latest", "demo-backend": PROJECT + "-backend:" + tag}
        if cfg.get("image") != images[service]:
            raise ValueError("Image target differs from the demo configuration")
        ports = cfg.get("ports", [])
        if service == "demo-frontend":
            if len(ports) != 1 or ports[0].get("host_ip") != "127.0.0.1" or str(ports[0].get("published")) != "8081" or ports[0].get("target") != 80:
                raise ValueError("Frontend must bind only localhost:8081")
        elif ports:
            raise ValueError("Only frontend may publish a host port")
    for kind, name in (("networks", NETWORK), ("volumes", VOLUME)):
        if set(data.get(kind, {})) != {name} or data[kind][name].get("name") != name or data[kind][name].get("external"):
            raise ValueError("Unexpected or external persistent resource")
    return data


def verify_release(release: Path) -> dict:
    reject_symlinks(release)
    if release.parent != ROOT / "releases" or not re.fullmatch(r"[a-f0-9]{16}", release.name):
        raise ValueError("Not an approved demo release path")
    if json.loads((ROOT / ".demo-root.json").read_text()) != {"project": PROJECT}:
        raise ValueError("Missing demo root identity")
    expected = json.loads((release / "release-hashes.json").read_text())
    hashes = source_hashes(release)
    if hashes != expected or release_id(hashes) != release.name:
        raise ValueError("Release source hashes do not match")
    return hashes
