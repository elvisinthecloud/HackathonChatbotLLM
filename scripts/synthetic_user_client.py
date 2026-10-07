#!/usr/bin/env python3
"""Small, serialized client for real synthetic conversations over the VM tunnel.

The client deliberately talks only to a loopback ``/api`` endpoint.  It records
the response returned by the API verbatim after every turn, including failed
HTTP requests, so an adaptive test can inspect the real answer without this
helper inventing one.
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import tempfile
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


DEFAULT_API_BASE_URL = "http://127.0.0.1:18081/api"
DEFAULT_REPORT_DIR = Path.home() / ".codex" / "hackathon-synthetic-20261002"
DEFAULT_LOCK_PATH = DEFAULT_REPORT_DIR / "api.lock"
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")
SCENARIO_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$")
PROFILE_IDS = frozenset(
    {"student", "instructor", "ao", "training-manager", "regional-director"}
)
ISSUE_CATEGORIES = frozenset(
    {"Account/Profile Issue", "Courseware Issue", "Roles and Permissions", "Other"}
)
MAX_HTTP_BODY = 8 * 1024 * 1024


class _NoRedirectHandler(HTTPRedirectHandler):
    """The tunnel API must never redirect a request off loopback."""

    def redirect_request(self, *_args, **_kwargs):
        return None


_HTTP = build_opener(_NoRedirectHandler)


class SyntheticClientError(RuntimeError):
    """Base class for bounded client and transcript errors."""


class LockTimeout(SyntheticClientError):
    """The shared advisory lock was not available within its deadline."""


class TranscriptError(SyntheticClientError):
    """A report could not be created or failed its schema checks."""


@dataclass(frozen=True)
class SyntheticSession:
    """Immutable identity used for every turn in one synthetic conversation."""

    scenario_id: str
    profile_id: str
    session_id: str
    transcript_path: Path | None = None


@dataclass(frozen=True)
class TurnResult:
    """Recorded result of one real HTTP chat request."""

    status: int | None
    elapsed_ms: int
    response: dict[str, Any] | None
    error: Any
    record: dict[str, Any]

    @property
    def answer(self) -> str | None:
        """Return the server answer, or None when no real answer was returned."""

        if self.response is None:
            return None
        value = self.response.get("answer")
        return value if isinstance(value, str) else None

    @property
    def suggested_replies(self) -> list[str] | None:
        """Return suggestions only when they were present in the API response."""

        if self.response is None:
            return None
        value = self.response.get("suggested_replies")
        return value if isinstance(value, list) else None


class AdvisoryFileLock:
    """Cross-process, non-blocking advisory lock with a bounded wait."""

    def __init__(self, path: Path, timeout_s: float = 300.0, poll_s: float = 0.05):
        if timeout_s <= 0 or timeout_s > 300:
            raise ValueError("lock timeout must be between 0 and 300 seconds")
        self.path = Path(path).expanduser().resolve()
        self.timeout_s = float(timeout_s)
        self.poll_s = max(0.01, min(float(poll_s), 1.0))
        self._handle = None

    def __enter__(self) -> "AdvisoryFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise SyntheticClientError("shared lock path cannot be a symlink")
        self._handle = self.path.open("a+")
        os.chmod(self.path, 0o600)
        deadline = time.monotonic() + self.timeout_s
        while True:
            try:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    self._handle.close()
                    self._handle = None
                    raise LockTimeout("shared synthetic API lock timed out") from None
                time.sleep(min(self.poll_s, max(0.0, deadline - time.monotonic())))

    def __exit__(self, *_: object) -> None:
        if self._handle is not None:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None


def _validate_api_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("API base URL must be an HTTP loopback URL")
    if parsed.query or parsed.fragment or parsed.path.rstrip("/") != "/api":
        raise ValueError("API base URL must end at the local /api endpoint")
    host = parsed.hostname
    if not host:
        raise ValueError("API base URL must have a loopback host")
    is_loopback_name = host.lower() == "localhost"
    try:
        is_loopback_address = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback_address = False
    if not (is_loopback_name or is_loopback_address):
        raise ValueError("API base URL must use a loopback host")
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("API base URL has an invalid port") from None
    if port is None:
        port = 80
    if not 1 <= port <= 65535:
        raise ValueError("API base URL has an invalid port")
    return value.rstrip("/")


def _validate_profile(profile_id: str) -> str:
    if profile_id not in PROFILE_IDS:
        raise ValueError("unknown demo profile")
    return profile_id


def _validate_scenario(scenario_id: str) -> str:
    if not SCENARIO_PATTERN.fullmatch(scenario_id):
        raise ValueError("scenario ID must be a short identifier")
    return scenario_id


def _validate_session_id(session_id: str) -> str:
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError("invalid demo session ID")
    return session_id


def _external_report_path(path: Path) -> Path:
    candidate = Path(path).expanduser().resolve()
    project_root = Path(__file__).resolve().parents[1]
    try:
        candidate.relative_to(project_root)
    except ValueError:
        pass
    else:
        raise TranscriptError("transcripts must be stored outside the project checkout")
    if candidate.exists() and candidate.is_dir():
        raise TranscriptError("transcript path must be a file")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def _read_json_body(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"raw_body": raw.decode("utf-8", errors="replace")}


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path = _external_report_path(path)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".synthetic-", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except (UnboundLocalError, OSError):
            pass
        raise TranscriptError("could not write synthetic transcript") from exc


class SyntheticUserClient:
    """Issue real API requests while serializing model work for all test agents."""

    def __init__(
        self,
        base_url: str = DEFAULT_API_BASE_URL,
        *,
        timeout_s: float = 240.0,
        lock_path: Path = DEFAULT_LOCK_PATH,
        lock_timeout_s: float = 300.0,
    ):
        if timeout_s <= 0 or timeout_s > 300:
            raise ValueError("request timeout must be between 0 and 300 seconds")
        self.base_url = _validate_api_base_url(base_url)
        self.timeout_s = float(timeout_s)
        self.lock_path = Path(lock_path)
        self.lock_timeout_s = float(lock_timeout_s)

    def _post(self, endpoint: str, payload: dict[str, Any]) -> tuple[int | None, int, Any, Any]:
        # All callers hold the shared lock. Space even instant clarifications
        # and session creation so synthetic agents do not burst through nginx.
        time.sleep(1.1)
        if endpoint not in {"sessions", "chat"}:
            raise ValueError("unsupported demo endpoint")
        request = Request(
            f"{self.base_url}/{endpoint}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.monotonic()
        try:
            with _HTTP.open(request, timeout=self.timeout_s) as response:
                body = response.read(MAX_HTTP_BODY + 1)
                elapsed_ms = int(round((time.monotonic() - started) * 1000))
                if len(body) > MAX_HTTP_BODY:
                    return response.status, elapsed_ms, None, {"type": "ResponseTooLarge"}
                return response.status, elapsed_ms, _read_json_body(body), None
        except HTTPError as exc:
            try:
                body = exc.read(MAX_HTTP_BODY + 1)
            finally:
                exc.close()
            elapsed_ms = int(round((time.monotonic() - started) * 1000))
            if len(body) > MAX_HTTP_BODY:
                return exc.code, elapsed_ms, None, {"type": "ResponseTooLarge"}
            parsed = _read_json_body(body)
            return exc.code, elapsed_ms, None, parsed if parsed is not None else {"type": "HTTPError"}
        except (TimeoutError, socket.timeout):
            elapsed_ms = int(round((time.monotonic() - started) * 1000))
            return None, elapsed_ms, None, {"type": "TimeoutError", "message": "request timed out"}
        except URLError:
            elapsed_ms = int(round((time.monotonic() - started) * 1000))
            return None, elapsed_ms, None, {"type": "ConnectionError", "message": "API request failed"}
        except OSError:
            elapsed_ms = int(round((time.monotonic() - started) * 1000))
            return None, elapsed_ms, None, {"type": "ConnectionError", "message": "API request failed"}

    def start_session(
        self,
        profile_id: str,
        *,
        scenario_id: str,
        course_id: str | None = None,
        transcript_path: Path | None = None,
    ) -> SyntheticSession:
        """Create a fresh server session and optionally initialize its report."""

        profile_id = _validate_profile(profile_id)
        scenario_id = _validate_scenario(scenario_id)
        report_path = _external_report_path(transcript_path) if transcript_path else None
        if report_path and report_path.exists():
            raise TranscriptError("refusing to overwrite an existing transcript")
        payload = {"profile_id": profile_id, "course_id": course_id}
        with AdvisoryFileLock(self.lock_path, self.lock_timeout_s):
            status, elapsed_ms, response, error = self._post("sessions", payload)
            if status is None or not 200 <= status < 300 or not isinstance(response, dict):
                raise SyntheticClientError("could not create demo session")
            session_id = response.get("session_id")
            if not isinstance(session_id, str) or not SESSION_ID_PATTERN.fullmatch(session_id):
                raise SyntheticClientError("demo session response had an invalid session ID")
            session = SyntheticSession(scenario_id, profile_id, session_id, report_path)
            if report_path:
                _write_json_atomic(
                    report_path,
                    {
                        "schema": 1,
                        "producer": "synthetic_user_client",
                        "scenario_id": scenario_id,
                        "profile": profile_id,
                        "session_id": session_id,
                        "session_request": {"status": status, "elapsed_ms": elapsed_ms},
                        "turns": [],
                    },
                )
            return session

    def attach_session(
        self,
        profile_id: str,
        session_id: str,
        *,
        scenario_id: str,
        transcript_path: Path | None = None,
    ) -> SyntheticSession:
        """Attach to a caller-owned report without fetching any prior server history."""

        profile_id = _validate_profile(profile_id)
        scenario_id = _validate_scenario(scenario_id)
        session_id = _validate_session_id(session_id)
        report_path = _external_report_path(transcript_path) if transcript_path else None
        if report_path:
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise TranscriptError("could not read synthetic transcript") from exc
            if (
                not isinstance(report, dict)
                or report.get("schema") != 1
                or report.get("producer") != "synthetic_user_client"
                or report.get("profile") != profile_id
                or report.get("session_id") != session_id
                or report.get("scenario_id") != scenario_id
                or not isinstance(report.get("turns"), list)
            ):
                raise TranscriptError("transcript identity or schema does not match")
        return SyntheticSession(scenario_id, profile_id, session_id, report_path)

    def append_turn(
        self,
        session: SyntheticSession,
        message: str,
        *,
        course_id: str | None = None,
        issue_category: str | None = None,
        image: str | None = None,
    ) -> TurnResult:
        """Append one real chat turn and return the exact recorded API result."""

        if not isinstance(message, str):
            raise TypeError("message must be text")
        if issue_category is not None and issue_category not in ISSUE_CATEGORIES:
            raise ValueError("unknown issue category")
        payload: dict[str, Any] = {
            "session_id": _validate_session_id(session.session_id),
            "message": message,
            "course_id": course_id,
            "issue_category": issue_category,
        }
        if image is not None:
            payload["image"] = image
        with AdvisoryFileLock(self.lock_path, self.lock_timeout_s):
            status, elapsed_ms, body, error = self._post("chat", payload)
            response = (
                body
                if status is not None
                and 200 <= status < 300
                and isinstance(body, dict)
                and {"session_id", "answer", "sources", "retrieved_count"}.issubset(body)
                else None
            )
            if response is not None and response.get("session_id") != session.session_id:
                error = {"type": "SessionMismatch", "body": body}
                response = None
            if status is not None and 200 <= status < 300 and response is None:
                if error is None:
                    error = {"type": "InvalidResponse", "body": body}
            record: dict[str, Any] = {
                "turn": 1,
                "message": message,
                "request": {key: value for key, value in payload.items() if key != "session_id"},
                "status": status,
                "elapsed_ms": elapsed_ms,
                "response": response,
            }
            if error is not None:
                record["error"] = error
            if response is not None:
                for key in (
                    "answer",
                    "suggested_replies",
                    "sources",
                    "context",
                    "response_kind",
                    "retrieved_count",
                    "trace_id",
                    "needs_clarification",
                    "matched_bucket_id",
                    "session_id",
                ):
                    if key in response:
                        record[key] = response[key]
            if session.transcript_path:
                report = json.loads(session.transcript_path.read_text(encoding="utf-8"))
                if not isinstance(report, dict) or not isinstance(report.get("turns"), list):
                    raise TranscriptError("transcript schema is invalid")
                if report.get("profile") != session.profile_id or report.get("session_id") != session.session_id:
                    raise TranscriptError("transcript identity changed")
                record["turn"] = len(report["turns"]) + 1
                report["turns"].append(record)
                _write_json_atomic(session.transcript_path, report)
            return TurnResult(status, elapsed_ms, response, error, record)


def _read_image(path: Path) -> str:
    """Encode one caller-supplied PNG/JPEG/WebP without printing its contents."""

    raw = Path(path).read_bytes()
    return base64.b64encode(raw).decode("ascii")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--profile", required=True, choices=sorted(PROFILE_IDS))
    parser.add_argument("--message", required=True)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--session-id", help="append to the matching existing transcript session")
    parser.add_argument("--course-id")
    parser.add_argument("--issue-category", choices=sorted(ISSUE_CATEGORIES))
    parser.add_argument("--image-file", type=Path)
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--lock-timeout", type=float, default=300.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    client = SyntheticUserClient(args.base_url, timeout_s=args.timeout, lock_timeout_s=args.lock_timeout)
    if args.session_id:
        session = client.attach_session(
            args.profile,
            args.session_id,
            scenario_id=args.scenario_id,
            transcript_path=args.transcript,
        )
    else:
        session = client.start_session(
            args.profile,
            scenario_id=args.scenario_id,
            course_id=args.course_id,
            transcript_path=args.transcript,
        )
    image = _read_image(args.image_file) if args.image_file else None
    result = client.append_turn(
        session,
        args.message,
        course_id=args.course_id,
        issue_category=args.issue_category,
        image=image,
    )
    print(
        json.dumps(
            {
                "scenario_id": session.scenario_id,
                "profile": session.profile_id,
                "turn": result.record["turn"],
                "status": result.status,
                "elapsed_ms": result.elapsed_ms,
                "transcript_written": session.transcript_path is not None,
            },
            sort_keys=True,
        )
    )
    return 0 if result.status is not None and 200 <= result.status < 300 and result.response is not None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SyntheticClientError, OSError, ValueError) as exc:
        # Never include URLs, configuration, tokens, or response bodies in CLI errors.
        raise SystemExit("Synthetic API check failed: " + type(exc).__name__) from None
