"""Small server-owned transcripts in demo Postgres; raw screenshots are never stored."""
import hashlib
import json
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from db import get_connection
from demo_policy import PROFILES, COURSES

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS demo_sessions (
        id uuid PRIMARY KEY, token_hash text UNIQUE NOT NULL, profile_id text NOT NULL,
        selected_course_id text, context jsonb NOT NULL DEFAULT '{}'::jsonb,
        context_version integer NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL DEFAULT now()+interval '24 hours')""",
    """CREATE TABLE IF NOT EXISTS demo_turns (
        id bigserial PRIMARY KEY, session_id uuid NOT NULL REFERENCES demo_sessions(id),
        context_version integer NOT NULL, question text NOT NULL, answer text NOT NULL,
        image_text text NOT NULL DEFAULT '', had_image boolean NOT NULL DEFAULT false,
        trace_id text, context jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now())""",
    'CREATE INDEX IF NOT EXISTS demo_turns_session_idx ON demo_turns(session_id, id)',
)

class SessionMissing(ValueError):
    pass

class SessionCapacity(ValueError):
    pass


def ensure_schema(conn):
    # get_connection has already checked dedicated database identity and marker.
    for statement in SCHEMA:
        conn.execute(statement)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(profile_id, course_id):
    if profile_id not in PROFILES or (course_id is not None and len(course_id)>160):
        raise ValueError('Unknown demo profile or course')
    token=secrets.token_urlsafe(32)
    with get_connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(684922)')
        count=conn.execute('SELECT count(*) FROM demo_sessions WHERE expires_at>now()').fetchone()[0]
        if count>=500:
            raise SessionCapacity('Demo session capacity reached')
        conn.execute('INSERT INTO demo_sessions(id,token_hash,profile_id,selected_course_id) VALUES(%s,%s,%s,%s)',
                     (str(uuid4()),token_hash(token),profile_id,course_id))
    return {'session_id':token,'profile':PROFILES[profile_id],'course':COURSES.get(course_id)}


def load_session(token):
    with get_connection() as conn:
        row=conn.execute('SELECT id,profile_id,selected_course_id,context,context_version FROM demo_sessions WHERE token_hash=%s AND expires_at>now()',
                         (token_hash(token),)).fetchone()
        if row is None or row[1] not in PROFILES:
            raise SessionMissing('Demo session expired or missing')
        turns=conn.execute('SELECT question,answer,image_text,context_version,context FROM demo_turns WHERE session_id=%s ORDER BY id', (row[0],)).fetchall()
    if len(turns)>=100:
        raise SessionCapacity('This conversation has reached 100 turns. Start a new conversation.')
    return {'id':str(row[0]),'profile':PROFILES[row[1]],'selected_course_id':row[2],
            'context':row[3], 'version':row[4], 'turns':turns}


def context_memory(session, changed):
    if changed:
        return [], ''
    current=[t for t in session['turns'] if t[3]==session['version']]
    history=[]
    for question,answer,_,_,_ in current[-6:]:
        history.extend([{'role':'user','content':question[:4000]}, {'role':'assistant','content':answer[:6000]}])
    # Bound model context independently from the full retained transcript.
    total=0
    bounded=[]
    for item in reversed(history):
        if total+len(item['content'])>12000:
            break
        bounded.append(item)
        total+=len(item['content'])
    history=list(reversed(bounded))
    # Only user-reported or vision-transcribed evidence; never the assistant's guesses.
    evidence='\n'.join(t[0]+'\n'+t[2] for t in current)
    return history,evidence


def save_turn(session, selected_course_id, context, changed, question, image_text, had_image, result):
    from psycopg.types.json import Jsonb
    version=session['version']+int(changed)
    with get_connection() as conn:
        conn.execute('INSERT INTO demo_turns(session_id,context_version,question,answer,image_text,had_image,trace_id,context) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                     (session['id'],version,question,result['answer'],image_text[:8000],had_image,result.get('trace_id'),Jsonb(context)))
        conn.execute('UPDATE demo_sessions SET selected_course_id=%s,context=%s,context_version=%s WHERE id=%s',
                     (selected_course_id,Jsonb(context),version,session['id']))


def owns_trace(token, trace_id):
    with get_connection() as conn:
        return conn.execute('SELECT 1 FROM demo_turns t JOIN demo_sessions s ON s.id=t.session_id WHERE s.token_hash=%s AND s.expires_at>now() AND t.trace_id=%s',
                            (token_hash(token),trace_id)).fetchone() is not None
