import os
from contextlib import contextmanager
from typing import Iterator

from pgvector.psycopg import register_vector
from psycopg import Connection
from psycopg_pool import ConnectionPool
from demo_config import DATABASE_NAME, INSTANCE_ID, validate_runtime


DEMO_CONFIG = validate_runtime()
DATABASE_URL = DEMO_CONFIG.database_url

_pool: ConnectionPool | None = None


def _configure_connection(conn: Connection) -> None:
    target = conn.execute("SELECT current_database(), current_user").fetchone()
    if target != (DATABASE_NAME, DATABASE_NAME):
        raise RuntimeError("Database identity is not the dedicated demo database")
    marker = conn.execute("SELECT instance_id FROM demo_identity WHERE singleton = TRUE").fetchone()
    if marker != (INSTANCE_ID,):
        raise RuntimeError("Demo database identity marker is missing or incorrect")
    # psycopg needs this adapter before it can read or write pgvector values.
    register_vector(conn)
    conn.commit()


def init_pool() -> None:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=int(os.getenv("DB_POOL_MIN_SIZE", "1")),
            max_size=int(os.getenv("DB_POOL_MAX_SIZE", "5")),
            configure=_configure_connection,
            open=True,
            timeout=10,
        )
        _pool.wait(timeout=10)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_pool() -> ConnectionPool:
    if _pool is None:
        init_pool()
    assert _pool is not None
    return _pool


@contextmanager
def get_connection() -> Iterator[Connection]:
    with get_pool().connection() as conn:
        yield conn
