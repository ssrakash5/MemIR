"""Database schema and connection helpers for the eval/ generation harness.

Scope note (see CLAUDE.md "Current phase"): this schema supports the
minimal harness built to unblock labeling validation -- one row per
memory (including source facts and distractors, stored as depth=0 rows),
one row per (parent, child) influence edge with its oracle role. It is
not the full production schema for the 3,456-trace sweep; extend rather
than redesign when that work starts.
"""
import os

import psycopg
from pgvector.psycopg import register_vector

DEFAULT_DATABASE_URL = "postgresql://postgres:memoryir@localhost:5433/memoryir"

SCHEMA_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    """
    CREATE TABLE IF NOT EXISTS memories (
        id SERIAL PRIMARY KEY,
        scenario_id TEXT NOT NULL,
        trace_id TEXT NOT NULL,          -- one trace = one (scenario, derivation_transform, seed) generation run
        depth INT NOT NULL,
        branch TEXT NOT NULL,            -- 'source_fact', 'distractor', 'child_1' (true-descendant lineage), 'child_2' (clean sibling)
        local_id TEXT,                   -- P1/B1/B2/D1..D9 for depth-0 rows; NULL for derived memories
        content TEXT NOT NULL,
        embedding VECTOR({embed_dim}),
        derivation_transform TEXT,
        prompt_style TEXT,
        model TEXT,                      -- which LLM generated this write (added 2026-08-12 for
                                                 -- the 3-model cross-model extension; NULL on any row
                                                 -- predating this column means gpt-4o-mini -- see the
                                                 -- backfill migration statement below).
        content_label TEXT,              -- CARRIES/REFERENCES/CLEAN -- filled in by the labeler, NULL at generation time
        derivation_contract_satisfied BOOLEAN,  -- did this write express its target_semantics, distinct from content_label
                                                 -- (added 2026-08-12; see docs/labeling_protocol.md's compositional-target rule --
                                                 -- a multi_hop_setup child can be structurally on-contract, using all
                                                 -- intended parents, while still failing to compose them into the
                                                 -- target proposition, i.e. content_label=REFERENCES not CARRIES).
                                                 -- NULL at generation time, filled in alongside content_label.
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # Migration for tables created before derivation_contract_satisfied
    # existed (CREATE TABLE IF NOT EXISTS doesn't alter an existing table).
    "ALTER TABLE memories ADD COLUMN IF NOT EXISTS derivation_contract_satisfied BOOLEAN",
    "ALTER TABLE memories ADD COLUMN IF NOT EXISTS model TEXT",
    # Backfill: every row generated before this column existed was gpt-4o-mini
    # (the only model used prior to the 2026-08-12 cross-model extension).
    "UPDATE memories SET model='gpt-4o-mini' WHERE model IS NULL AND branch IN ('child_1','child_2','child_3')",
    "CREATE INDEX IF NOT EXISTS idx_memories_trace ON memories(trace_id)",
    "CREATE INDEX IF NOT EXISTS idx_memories_scenario ON memories(scenario_id)",
    """
    CREATE TABLE IF NOT EXISTS memory_influence (
        id SERIAL PRIMARY KEY,
        trace_id TEXT NOT NULL,
        parent_memory_id INT NOT NULL REFERENCES memories(id),
        child_memory_id INT NOT NULL REFERENCES memories(id),
        role TEXT NOT NULL CHECK (role IN ('STRUCTURAL_PARENT', 'CO_RETRIEVED')),
        depth INT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_influence_trace ON memory_influence(trace_id)",
    "CREATE INDEX IF NOT EXISTS idx_influence_child ON memory_influence(child_memory_id)",
    # parent_memory_id has an FK to memories(id) but no supporting index --
    # without one, deleting from memories forces Postgres to sequential-scan
    # all of memory_influence per deleted row to check the FK. Added
    # 2026-09-21 after eval/invalidate_clean_control_scenarios.py's delete
    # stalled >13 minutes on this at ~1.8M memory_influence rows.
    "CREATE INDEX IF NOT EXISTS idx_influence_parent ON memory_influence(parent_memory_id)",
    # Full-sweep checkpoint tracking (added 2026-08-12). One row per
    # enumerated (scenario_id, top_k, write_fanout, derivation_transform,
    # seed) trace key -- the durable resume/dedup mechanism for
    # eval/run_full_sweep.py. `attempts` counts retries of the SAME trace
    # key/seed (never an extra statistical replicate -- see
    # docs/preregistration.md SS4's frozen seed rules).
    """
    CREATE TABLE IF NOT EXISTS sweep_runs (
        trace_id TEXT PRIMARY KEY,
        scenario_id TEXT NOT NULL,
        top_k INT NOT NULL,
        write_fanout INT NOT NULL,
        derivation_transform TEXT NOT NULL,
        seed INT NOT NULL,
        model TEXT NOT NULL DEFAULT 'gpt-4o-mini',
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'running', 'done', 'failed', 'error_exhausted')),
        attempts INT NOT NULL DEFAULT 0,
        last_error TEXT,
        claimed_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_sweep_runs_status ON sweep_runs(status)",
    "ALTER TABLE sweep_runs ADD COLUMN IF NOT EXISTS model TEXT NOT NULL DEFAULT 'gpt-4o-mini'",
]


def connect(database_url: str | None = None, *, embed_dim: int) -> psycopg.Connection:
    url = database_url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    conn = psycopg.connect(url, autocommit=True)
    register_vector(conn)
    for stmt in SCHEMA_STATEMENTS:
        conn.execute(stmt.format(embed_dim=embed_dim))
    return conn


def insert_memory(
    conn: psycopg.Connection,
    *,
    scenario_id: str,
    trace_id: str,
    depth: int,
    branch: str,
    local_id: str | None,
    content: str,
    embedding: list[float],
    derivation_transform: str | None = None,
    prompt_style: str | None = None,
    model: str | None = None,
) -> int:
    row = conn.execute(
        """
        INSERT INTO memories
            (scenario_id, trace_id, depth, branch, local_id, content, embedding,
             derivation_transform, prompt_style, model)
        VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s)
        RETURNING id
        """,
        (
            scenario_id,
            trace_id,
            depth,
            branch,
            local_id,
            content,
            embedding,
            derivation_transform,
            prompt_style,
            model,
        ),
    ).fetchone()
    return row[0]


def seed_sweep_runs(conn: psycopg.Connection, cells: list[dict]) -> None:
    """Upsert every enumerated trace key as 'pending', preserving existing
    rows' status (ON CONFLICT DO NOTHING) -- safe to call on every launch,
    including resumes, without touching already-done/failed rows."""
    with conn.cursor() as cur:
        for c in cells:
            cur.execute(
                """
                INSERT INTO sweep_runs
                    (trace_id, scenario_id, top_k, write_fanout, derivation_transform, seed, model)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trace_id) DO NOTHING
                """,
                (c["trace_id"], c["scenario_id"], c["top_k"], c["write_fanout"],
                 c["derivation_transform"], c["seed"], c.get("model", "gpt-4o-mini")),
            )


def reset_stuck_running(conn: psycopg.Connection) -> int:
    """Any row still 'running' at process start belongs to a crashed prior
    process -- reset to 'pending' so it's reclaimed (and its partial rows
    wiped by delete_trace_rows before regeneration, see run_full_sweep.py)."""
    row = conn.execute(
        "UPDATE sweep_runs SET status='pending' WHERE status='running' RETURNING trace_id"
    ).fetchall()
    return len(row)


def claim_trace(conn: psycopg.Connection, trace_id: str, *, max_attempts: int) -> bool:
    """Atomically claim one trace for this worker. Returns False if it's
    already done, already claimed by another worker, or has exhausted
    max_attempts (marked 'error_exhausted' and left for manual review)."""
    row = conn.execute(
        """
        UPDATE sweep_runs
        SET status='running', claimed_at=now(), attempts=attempts+1
        WHERE trace_id=%s AND status IN ('pending','failed') AND attempts < %s
        RETURNING trace_id
        """,
        (trace_id, max_attempts),
    ).fetchone()
    if row is None:
        conn.execute(
            "UPDATE sweep_runs SET status='error_exhausted' "
            "WHERE trace_id=%s AND status='failed' AND attempts >= %s",
            (trace_id, max_attempts),
        )
    return row is not None


def mark_done(conn: psycopg.Connection, trace_id: str) -> None:
    conn.execute(
        "UPDATE sweep_runs SET status='done', completed_at=now() WHERE trace_id=%s",
        (trace_id,),
    )


def mark_failed(conn: psycopg.Connection, trace_id: str, error: str) -> None:
    conn.execute(
        "UPDATE sweep_runs SET status='failed', last_error=%s WHERE trace_id=%s",
        (error[:4000], trace_id),
    )


def delete_trace_rows(conn: psycopg.Connection, trace_id: str) -> None:
    """Wipe any partial rows from a prior crashed/failed attempt at this
    exact trace_id before regenerating -- makes retry idempotent instead
    of accumulating duplicate memory rows."""
    conn.execute("DELETE FROM memory_influence WHERE trace_id=%s", (trace_id,))
    conn.execute("DELETE FROM memories WHERE trace_id=%s", (trace_id,))


def sweep_status_counts(conn: psycopg.Connection) -> dict:
    rows = conn.execute("SELECT status, count(*) FROM sweep_runs GROUP BY status").fetchall()
    return dict(rows)


def insert_influence_edges(
    conn: psycopg.Connection,
    *,
    trace_id: str,
    child_memory_id: int,
    depth: int,
    structural_parent_ids: list[int],
    co_retrieved_ids: list[int],
) -> None:
    with conn.cursor() as cur:
        for pid in structural_parent_ids:
            cur.execute(
                "INSERT INTO memory_influence (trace_id, parent_memory_id, child_memory_id, role, depth) "
                "VALUES (%s, %s, %s, 'STRUCTURAL_PARENT', %s)",
                (trace_id, pid, child_memory_id, depth),
            )
        for pid in co_retrieved_ids:
            cur.execute(
                "INSERT INTO memory_influence (trace_id, parent_memory_id, child_memory_id, role, depth) "
                "VALUES (%s, %s, %s, 'CO_RETRIEVED', %s)",
                (trace_id, pid, child_memory_id, depth),
            )
