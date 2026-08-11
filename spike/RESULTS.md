# Spike Results

| Script | Status | Notes |
|---|---|---|
| `01_db.py` | GREEN | Postgres 16 + pgvector via Docker (`pgvector/pgvector:pg16`, container `memoryir-pg`, host port 5433 — 5432 was already taken by an unrelated container on this machine). `VECTOR` column create, insert, and `<->` ANN query all work. Note: `psycopg` needs explicit `::vector` casts on query parameters (`%s::vector`) — the bare-list adapter registered by `pgvector.psycopg.register_vector` did not implicitly cast on the query side in this psycopg 3.2.9 / pgvector-python 0.5.0 combination. |
| `02_embed.py` | Not started | Blocked on an embedding/LLM API key. |
| `03_cte.py` | GREEN | Recursive CTE with array path + depth cap tested on both a plain linear chain (depth cap correctly truncates) and a deliberately cyclic graph (1→2→3→1, plus 3→4). Cycle guard (`NOT (child = ANY(path))`) correctly reaches each of the 4 nodes exactly once and terminates — confirms the plan's specific warning (adding a `path`/`depth` column defeats a naive `id`-only cycle check) does NOT apply here because the guard checks membership in `path`, not row identity. Added a 5s `statement_timeout` as a belt-and-suspenders guard in case a future edit reintroduces the footgun. |
| `04_llm.py` | Not started | Blocked on an embedding/LLM API key. |
| `05_e2e.py` | Not started | Blocked on `02` and `04`. |

## Environment

- Docker container: `memoryir-pg` (`pgvector/pgvector:pg16`), `postgresql://postgres:memoryir@localhost:5433/memoryir`
- This container is a local dev convenience, not committed anywhere — anyone re-running these spikes needs to `docker run` it themselves (see command in git history / ask for it to be added to a `docker-compose.yml` if this becomes a recurring need past week 1).
- Python 3.10.7, `psycopg[binary]` 3.2.9, `pgvector` (Python) 0.5.0

## Outstanding

`02_embed.py`, `04_llm.py`, `05_e2e.py` need an embedding/LLM API key
(e.g. `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` env var) before they can be
written and run. Until those are GREEN, the Sunday gate's "spike/RESULTS.md
all GREEN or documented-YELLOW" condition is not met — 3 of 5 scripts
haven't been attempted yet, which is different from YELLOW (attempted, works
with a caveat).
