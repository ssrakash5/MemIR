"""Spike: Postgres + pgvector up, VECTOR column, insert, ANN query.

Verifies the base storage layer works before anything else is built on it.
Exits 0 on success, non-zero (with a traceback) on failure.
"""
import os

import psycopg
from pgvector.psycopg import register_vector

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:memoryir@localhost:5433/memoryir"
)
DIM = 8  # small dimension for the spike; real embedding_model dim is TBD


def main() -> None:
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)

    conn.execute("DROP TABLE IF EXISTS spike_memories")
    conn.execute(
        f"CREATE TABLE spike_memories (id serial PRIMARY KEY, content text, embedding vector({DIM}))"
    )

    rows = [
        ("memory about cats", [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ("memory about dogs", [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ("memory about cars", [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    ]
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO spike_memories (content, embedding) VALUES (%s, %s)",
            rows,
        )

    query_vec = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    result = conn.execute(
        "SELECT content, embedding <-> %s::vector AS distance "
        "FROM spike_memories ORDER BY embedding <-> %s::vector LIMIT 2",
        (query_vec, query_vec),
    ).fetchall()

    assert len(result) == 2, f"expected 2 ANN results, got {len(result)}"
    assert result[0][0] == "memory about cats", f"nearest neighbor wrong: {result[0]}"
    assert result[0][1] < result[1][1], "results not sorted by distance"

    conn.execute("DROP TABLE spike_memories")
    conn.close()
    print("GREEN: pgvector extension, VECTOR column, insert, and ANN query all work.")
    print(f"  Nearest neighbor to query: {result[0][0]} (distance={result[0][1]:.4f})")


if __name__ == "__main__":
    main()
