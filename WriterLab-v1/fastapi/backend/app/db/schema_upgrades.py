from sqlalchemy import text


SCHEMA_UPGRADES = [
    "ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS project_id UUID NULL",
    "ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS task_type VARCHAR(50) NULL",
    "ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS provider VARCHAR(50) NULL",
    "ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(100) NULL",
    "ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS fallback_used BOOLEAN NULL",
    "ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS token_usage JSONB NULL",
    "ALTER TABLE model_profiles ADD COLUMN IF NOT EXISTS workflow_step VARCHAR(50) NULL",
    "ALTER TABLE model_profiles ADD COLUMN IF NOT EXISTS api_base VARCHAR(255) NULL",
    "ALTER TABLE model_profiles ADD COLUMN IF NOT EXISTS api_key_env VARCHAR(100) NULL",
    "ALTER TABLE model_profiles ADD COLUMN IF NOT EXISTS routing_weight INTEGER NOT NULL DEFAULT 100",
    "ALTER TABLE model_profiles ADD COLUMN IF NOT EXISTS requests_per_minute INTEGER NULL",
    "ALTER TABLE model_profiles ADD COLUMN IF NOT EXISTS monthly_budget_usd DOUBLE PRECISION NULL",
    "ALTER TABLE model_profiles ADD COLUMN IF NOT EXISTS extra_headers JSONB NULL",
    "ALTER TABLE model_profiles ADD COLUMN IF NOT EXISTS capabilities JSONB NULL",
    """
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
            CREATE EXTENSION IF NOT EXISTS vector;
        END IF;
    EXCEPTION
        WHEN insufficient_privilege THEN NULL;
        WHEN undefined_table THEN NULL;
    END $$;
    """,
    """
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = 'knowledge_chunks'
        ) AND EXISTS (
            SELECT 1
            FROM pg_type
            WHERE typname = 'vector'
        ) THEN
            ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector(128) NULL;
            CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_vector
            ON knowledge_chunks
            USING ivfflat (embedding_vector vector_cosine_ops)
            WITH (lists = 100);
        END IF;
    EXCEPTION
        WHEN undefined_table THEN NULL;
        WHEN undefined_object THEN NULL;
        WHEN feature_not_supported THEN NULL;
    END $$;
    """,
    """
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'workflow_runs') THEN
            ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS queued_at TIMESTAMP NULL;
            ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMP NULL;
            ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMP NULL;
            ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS cancel_requested_at TIMESTAMP NULL;
            ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP NULL;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'workflow_steps') THEN
            ALTER TABLE workflow_steps ADD COLUMN IF NOT EXISTS fallback_used BOOLEAN NULL;
            ALTER TABLE workflow_steps ADD COLUMN IF NOT EXISTS guardrail_blocked BOOLEAN NULL;
            ALTER TABLE workflow_steps ADD COLUMN IF NOT EXISTS started_at TIMESTAMP NULL;
            ALTER TABLE workflow_steps ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP NULL;
            ALTER TABLE workflow_steps ADD COLUMN IF NOT EXISTS duration_ms INTEGER NULL;
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'consistency_issues') THEN
            ALTER TABLE consistency_issues ADD COLUMN IF NOT EXISTS source VARCHAR(50) NULL;
            ALTER TABLE consistency_issues ADD COLUMN IF NOT EXISTS fix_suggestion TEXT NULL;
        END IF;
    EXCEPTION
        WHEN undefined_table THEN NULL;
    END $$;
    """,
    """
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'model_profiles' AND column_name = 'temperature'
        ) THEN
            ALTER TABLE model_profiles
            ALTER COLUMN temperature TYPE DOUBLE PRECISION
            USING temperature::double precision;
        END IF;
    EXCEPTION
        WHEN undefined_table THEN NULL;
    END $$;
    """,
    """
    CREATE TABLE IF NOT EXISTS timeline_events (
        id UUID PRIMARY KEY,
        project_id UUID NOT NULL REFERENCES projects(id),
        chapter_id UUID NULL REFERENCES chapters(id),
        scene_id UUID NULL REFERENCES scenes(id),
        title VARCHAR(200) NOT NULL,
        event_type VARCHAR(50) NOT NULL DEFAULT 'incident',
        description TEXT NOT NULL,
        participants JSONB NULL,
        event_time_label VARCHAR(100) NULL,
        canonical BOOLEAN NOT NULL DEFAULT TRUE,
        metadata_json JSONB NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS style_memories (
        id UUID PRIMARY KEY,
        project_id UUID NOT NULL REFERENCES projects(id),
        scene_id UUID NULL REFERENCES scenes(id),
        memory_type VARCHAR(50) NOT NULL DEFAULT 'style_rule',
        content TEXT NOT NULL,
        source_excerpt TEXT NULL,
        derived_rules JSONB NULL,
        user_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
        status VARCHAR(50) NOT NULL DEFAULT 'suggested',
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS story_branches (
        id UUID PRIMARY KEY,
        project_id UUID NOT NULL REFERENCES projects(id),
        name VARCHAR(200) NOT NULL,
        description TEXT NULL,
        parent_branch_id UUID NULL REFERENCES story_branches(id),
        source_scene_id UUID NULL REFERENCES scenes(id),
        source_version_id UUID NULL REFERENCES scene_versions(id),
        latest_version_id UUID NULL REFERENCES scene_versions(id),
        status VARCHAR(50) NOT NULL DEFAULT 'active',
        metadata_json JSONB NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_runs (
        id UUID PRIMARY KEY,
        project_id UUID NULL REFERENCES projects(id),
        scene_id UUID NULL REFERENCES scenes(id),
        branch_id UUID NULL REFERENCES story_branches(id),
        run_type VARCHAR(50) NOT NULL DEFAULT 'scene_pipeline',
        status VARCHAR(50) NOT NULL DEFAULT 'queued',
        current_step VARCHAR(50) NULL,
        input_payload JSONB NULL,
        output_payload JSONB NULL,
        error_message TEXT NULL,
        retry_count INTEGER NOT NULL DEFAULT 0,
        queued_at TIMESTAMP NULL,
        heartbeat_at TIMESTAMP NULL,
        lease_expires_at TIMESTAMP NULL,
        cancel_requested_at TIMESTAMP NULL,
        cancelled_at TIMESTAMP NULL,
        started_at TIMESTAMP NULL,
        completed_at TIMESTAMP NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_steps (
        id UUID PRIMARY KEY,
        workflow_run_id UUID NOT NULL REFERENCES workflow_runs(id),
        step_key VARCHAR(50) NOT NULL,
        step_order INTEGER NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'queued',
        provider VARCHAR(50) NULL,
        model VARCHAR(200) NULL,
        input_payload JSONB NULL,
        output_payload JSONB NULL,
        error_message TEXT NULL,
        fallback_used BOOLEAN NULL,
        guardrail_blocked BOOLEAN NULL,
        started_at TIMESTAMP NULL,
        completed_at TIMESTAMP NULL,
        duration_ms INTEGER NULL,
        latency_ms INTEGER NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS consistency_issues (
        id UUID PRIMARY KEY,
        project_id UUID NULL REFERENCES projects(id),
        scene_id UUID NULL REFERENCES scenes(id),
        workflow_run_id UUID NULL REFERENCES workflow_runs(id),
        issue_type VARCHAR(50) NOT NULL,
        severity VARCHAR(20) NOT NULL DEFAULT 'medium',
        source VARCHAR(50) NULL,
        fix_suggestion TEXT NULL,
        message TEXT NOT NULL,
        evidence_json JSONB NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'open',
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
    """,
]


def apply_schema_upgrades(engine) -> None:
    with engine.begin() as connection:
        for statement in SCHEMA_UPGRADES:
            connection.execute(text(statement))
