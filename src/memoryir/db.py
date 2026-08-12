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
        content_label TEXT,              -- CARRIES/REFERENCES/CLEAN -- filled in by the labeler, NULL at generation time
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
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
) -> int:
    row = conn.execute(
        """
        INSERT INTO memories
            (scenario_id, trace_id, depth, branch, local_id, content, embedding,
             derivation_transform, prompt_style)
        VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s, %s)
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
        ),
    ).fetchone()
    return row[0]


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
