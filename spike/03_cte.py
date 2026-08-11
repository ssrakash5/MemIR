"""Spike: recursive CTE with array path + depth cap + cycle test.

week1_execution_plan.md §5 flags a specific footgun: the CTE terminates on
cycles only while selecting `id` alone. Adding a `depth` or `path` column
makes every row distinct (because the path array differs), so a naive
cycle check re-admits nodes and the recursion never terminates on its own —
you need both the depth cap AND the "already in path" cycle guard, and this
script exists to prove the guard actually works, not just the happy path.
"""
import os

import psycopg

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:memoryir@localhost:5433/memoryir"
)

RECURSIVE_CTE = """
WITH RECURSIVE exposed AS (
  SELECT id, ARRAY[id] AS path, 0 AS depth
  FROM memories WHERE id = %(root)s
  UNION ALL
  SELECT e.child_memory_id, array_append(x.path, e.child_memory_id), x.depth + 1
  FROM exposed x
  JOIN memory_influence e ON e.parent_memory_id = x.id
  WHERE x.depth < %(depth_cap)s
    AND NOT (e.child_memory_id = ANY(x.path))
)
SELECT id, path, depth FROM exposed ORDER BY depth, id
"""


def setup_schema(conn: psycopg.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS memory_influence")
    conn.execute("DROP TABLE IF EXISTS memories")
    conn.execute("CREATE TABLE memories (id int PRIMARY KEY)")
    conn.execute(
        "CREATE TABLE memory_influence (parent_memory_id int, child_memory_id int)"
    )


def test_linear_chain(conn: psycopg.Connection) -> None:
    """Depth cap and path tracking behave on a plain, acyclic chain."""
    setup_schema(conn)
    conn.execute("INSERT INTO memories (id) SELECT generate_series(1, 6)")
    conn.execute(
        "INSERT INTO memory_influence (parent_memory_id, child_memory_id) "
        "VALUES (1,2), (2,3), (3,4), (4,5), (5,6)"
    )

    rows = conn.execute(RECURSIVE_CTE, {"root": 1, "depth_cap": 20}).fetchall()
    assert len(rows) == 6, f"expected 6 nodes in linear chain, got {len(rows)}"
    assert rows[-1] == (6, [1, 2, 3, 4, 5, 6], 5), f"unexpected deepest row: {rows[-1]}"
    print(f"  linear chain: {len(rows)} nodes reached, deepest = {rows[-1]}")

    capped = conn.execute(RECURSIVE_CTE, {"root": 1, "depth_cap": 2}).fetchall()
    assert len(capped) == 3, f"depth cap 2 should yield 3 nodes (depth 0,1,2), got {len(capped)}"
    print(f"  depth cap=2: {len(capped)} nodes reached (correctly capped)")


def test_cycle_terminates(conn: psycopg.Connection) -> None:
    """The actual regression case: a cyclic graph must not hang the query."""
    setup_schema(conn)
    conn.execute("INSERT INTO memories (id) SELECT generate_series(1, 4)")
    # 1 -> 2 -> 3 -> 1 (cycle), plus 3 -> 4 (a legitimate node past the cycle)
    conn.execute(
        "INSERT INTO memory_influence (parent_memory_id, child_memory_id) "
        "VALUES (1,2), (2,3), (3,1), (3,4)"
    )

    rows = conn.execute(RECURSIVE_CTE, {"root": 1, "depth_cap": 20}).fetchall()
    ids = sorted(r[0] for r in rows)
    assert ids == [1, 2, 3, 4], f"cyclic graph should reach exactly {{1,2,3,4}} once each, got {ids}"
    print(f"  cyclic graph: terminated correctly, reached nodes {ids} (no infinite loop)")


def main() -> None:
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    # Belt-and-suspenders: if the cycle guard is ever broken by a future
    # edit, fail loudly in 5s instead of hanging the session indefinitely.
    conn.execute("SET statement_timeout = '5s'")
    test_linear_chain(conn)
    test_cycle_terminates(conn)
    conn.execute("DROP TABLE IF EXISTS memory_influence")
    conn.execute("DROP TABLE IF EXISTS memories")
    conn.close()
    print("GREEN: recursive CTE with array path, depth cap, and cycle guard all work.")


if __name__ == "__main__":
    main()
