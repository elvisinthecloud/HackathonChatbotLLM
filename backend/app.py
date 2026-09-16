import os
import asyncio
import base64
import binascii
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from db import DEMO_CONFIG, close_pool, get_connection, init_pool
from demo_dataset import load_dataset, validate_taxonomy
from demo_policy import PROFILES, COURSES
from demo_sessions import create_session, load_session, save_turn, owns_trace, SessionMissing, SessionCapacity
from rag import (
    OllamaError,
    answer_question,
    is_valid_bucket_id,
    precompute_bucket_embeddings,
    settings,
    langfuse,
)


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    course_id: str | None = Field(default=None, max_length=160)
    issue_category: Literal["Account/Profile Issue", "Courseware Issue", "Roles and Permissions", "Other"] | None = None
    message: str = Field(min_length=1, max_length=4000)
    image: str | None = Field(default=None, max_length=5_592_408)

    @field_validator("image")
    @classmethod
    def valid_image(cls, value):
        if value is None:
            return value
        try:
            raw = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error):
            raise ValueError("Image must be base64-encoded") from None
        if not raw or len(raw) > 4 * 1024 * 1024:
            raise ValueError("Image must be at most 4 MiB")
        if not (raw.startswith(b"\x89PNG\r\n\x1a\n") or raw.startswith(b"\xff\xd8\xff") or (raw.startswith(b"RIFF") and raw[8:12] == b"WEBP")):
            raise ValueError("Use a PNG, JPEG, or WebP screenshot")
        return value


class Source(BaseModel):
    citation: int
    title: str
    source_path: str
    chunk_index: int
    score: float
    preview: str
    bucket_label: str | None = None
    category_path: list[str] = []


class ClarificationOption(BaseModel):
    bucket_id: str
    label: str


class ChatResponse(BaseModel):
    context: dict = Field(default_factory=dict)
    session_id: str
    answer: str
    sources: list[Source]
    retrieved_count: int
    trace_id: str | None = None
    needs_clarification: bool = False
    clarification_options: list[ClarificationOption] = Field(default_factory=list)
    matched_bucket_id: str | None = None


class ScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    trace_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    score: float = Field(ge=0, le=1)


class SupportInfo(BaseModel):
    ticket_url: str
    email: str
    phone: str
    hours: str


chat_lock = asyncio.Lock()


async def verify_langfuse_project() -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            os.environ["LANGFUSE_HOST"] + "/api/public/projects",
            auth=(os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"]),
        )
    if response.status_code != 200:
        raise RuntimeError("Dedicated demo Langfuse authentication failed")
    projects = response.json().get("data", [])
    if len(projects) != 1 or projects[0].get("id") != os.environ["LANGFUSE_PROJECT_ID"] or projects[0].get("name") != "MCeLE Hackathon Demo":
        raise RuntimeError("Langfuse credentials do not belong to the expected demo project")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        documents = load_dataset(DEMO_CONFIG.manifest)
        validate_taxonomy(DEMO_CONFIG.taxonomy)
        init_pool()
        with get_connection() as conn:
            rows = conn.execute("SELECT source_path, content_sha256, metadata FROM articles ORDER BY source_path").fetchall()
            expected = sorted((d["source_path"], d["content_sha256"], d["metadata"]) for d in documents)
            if rows != expected:
                raise RuntimeError("Demo index must contain exactly the current curated articles; run demo ingestion first")
        await verify_langfuse_project()
        await precompute_bucket_embeddings()
    except Exception:
        close_pool()
        raise RuntimeError("Demo startup verification failed; check dataset, database identity and dedicated Langfuse project") from None
    try:
        yield
    finally:
        langfuse.flush()
        close_pool()


app = FastAPI(title="MCeLE Support Demo", version="0.2.0", lifespan=lifespan,
              docs_url=None, redoc_url=None)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": "Check your message, history length, and screenshot format/size."})


async def check_ollama() -> tuple[bool, list[str]]:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
        if response.status_code >= 400:
            return False, []
        data = response.json()
        models = [
            item.get("name", "")
            for item in data.get("models", [])
            if isinstance(item, dict) and item.get("name")
        ]
        return True, models
    except Exception:
        return False, []


@app.get("/api/health")
async def health() -> dict[str, object]:
    db_ok = False
    chunk_count = 0
    try:
        with get_connection() as conn:
            chunk_count = conn.execute("SELECT count(*) FROM article_chunks").fetchone()[0]
            db_ok = True
    except Exception:
        db_ok = False

    ollama_ok, ollama_models = await check_ollama()

    return {
        "ok": db_ok and ollama_ok and chunk_count > 0,
        "database": db_ok,
        "ollama": ollama_ok,
        "chunk_count": chunk_count,
        "dataset_id": "mcele-curated-v1",
        "phase": "curated-demo",
    }



class SessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(min_length=1,max_length=40)
    course_id: str | None = Field(default=None,max_length=160)


@app.get("/api/profiles")
async def profiles():
    return {"profiles":list(PROFILES.values()),"courses":list(COURSES.values()),"identity_mode":"demo-profile-selection"}


@app.post("/api/sessions")
async def sessions(request: SessionRequest):
    try:
        return create_session(request.profile_id,request.course_id)
    except SessionCapacity:
        raise HTTPException(status_code=429,detail="Demo session capacity reached. Please try later.") from None
    except ValueError:
        raise HTTPException(status_code=400,detail="Choose a known demo profile and course.") from None
    except Exception:
        raise HTTPException(status_code=503,detail="Could not start a demo session. Please retry.") from None


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if chat_lock.locked():
        raise HTTPException(status_code=429, detail="The demo is answering another question. Please try again shortly.")
    async with chat_lock:
        try:
            session=load_session(request.session_id)
            result = await answer_question(
                message,
                session=session,
                selected_course_id=request.course_id,
                image=request.image,
                issue_category=request.issue_category,
            )
            save_turn(session,request.course_id,result["context"],result.pop("_context_changed"),message,
                      result.pop("_image_text"),request.image is not None,result)
            return ChatResponse(**result,session_id=request.session_id)
        except SessionMissing:
            raise HTTPException(status_code=404,detail="This demo session is missing or expired. Start a new conversation.") from None
        except SessionCapacity:
            raise HTTPException(status_code=409,detail="This conversation has reached its limit. Start a new conversation.") from None
        except OllamaError:
            raise HTTPException(status_code=502, detail="The model service could not complete the response. Please retry.") from None
        except Exception:
            raise HTTPException(status_code=500, detail="The demo could not complete the request. Please retry.") from None


@app.get("/api/support", response_model=SupportInfo)
async def support() -> SupportInfo:
    return SupportInfo(
        ticket_url=settings.support_ticket_url,
        email=settings.helpdesk_email,
        phone=settings.helpdesk_phone,
        hours=settings.helpdesk_hours,
    )


@app.post("/api/score")
async def score(request: ScoreRequest):
    if not owns_trace(request.session_id,request.trace_id):
        raise HTTPException(status_code=404,detail="Trace not found for this demo session.")
    try:
        langfuse.create_score(trace_id=request.trace_id, name="user-feedback", value=request.score)
        langfuse.flush()
        return {"ok": True}
    except Exception:
        raise HTTPException(status_code=502, detail="Demo feedback could not be recorded.") from None
