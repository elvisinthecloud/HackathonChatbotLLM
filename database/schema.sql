-- This schema must only be initialized in the dedicated demo container.
DO $$ BEGIN
    IF current_database() <> 'mcele_demo' OR current_user <> 'mcele_demo' THEN
        RAISE EXCEPTION 'Refusing schema initialization outside the demo database';
    END IF;
END $$;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS demo_identity (
    singleton boolean PRIMARY KEY DEFAULT TRUE CHECK (singleton = TRUE),
    instance_id text NOT NULL CHECK (instance_id = 'mcele-hackathon-demo')
);
INSERT INTO demo_identity(singleton, instance_id)
VALUES (TRUE, 'mcele-hackathon-demo') ON CONFLICT (singleton) DO NOTHING;

CREATE TABLE IF NOT EXISTS articles (
    id bigserial PRIMARY KEY,
    source_path text NOT NULL UNIQUE,
    title text NOT NULL,
    content_sha256 text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS article_chunks (
    id bigserial PRIMARY KEY,
    article_id bigint NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    content text NOT NULL,
    token_count integer NOT NULL DEFAULT 0,
    embedding vector(768) NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (article_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS article_chunks_embedding_hnsw_idx
    ON article_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS article_chunks_article_id_idx
    ON article_chunks (article_id);
