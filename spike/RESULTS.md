# Spike Results

| Script | Status | Notes |
|---|---|---|
| `01_db.py` | GREEN | Postgres 16 + pgvector via Docker (`pgvector/pgvector:pg16`, container `memoryir-pg`, host port 5433 — 5432 was already taken by an unrelated container on this machine). `VECTOR` column create, insert, and `<->` ANN query all work. Note: `psycopg` needs explicit `::vector` casts on query parameters (`%s::vector`) — the bare-list adapter registered by `pgvector.psycopg.register_vector` did not implicitly cast on the query side in this psycopg 3.2.9 / pgvector-python 0.5.0 combination. |
| `02_embed.py` | YELLOW | Uses a local `sentence-transformers` model (`all-MiniLM-L6-v2`, 384-dim), not a hosted embedding API — no API key was available at first, and this model's weights were already cached locally. **This is a placeholder, not the real study's embedding model** — `configs/experiment_grid.yaml` and `docs/preregistration.md` still have `embedding_model: TBD`. Also required `HF_HUB_OFFLINE=1` to skip a network metadata check that was hitting the same SSL issue as below. |
| `03_cte.py` | GREEN | Recursive CTE with array path + depth cap tested on both a plain linear chain (depth cap correctly truncates) and a deliberately cyclic graph (1→2→3→1, plus 3→4). Cycle guard (`NOT (child = ANY(path))`) correctly reaches each of the 4 nodes exactly once and terminates — confirms the plan's specific warning (adding a `path`/`depth` column defeats a naive `id`-only cycle check) does NOT apply here because the guard checks membership in `path`, not row identity. Added a 5s `statement_timeout` as a belt-and-suspenders guard in case a future edit reintroduces the footgun. |
| `04_llm.py` | YELLOW | Structured JSON-schema call against Azure OpenAI (`gpt-4o-mini` deployment), using credentials from `../creds.env` (outside this repo, gitignored regardless). Required a workaround: Python's `certifi` CA bundle doesn't trust this network's TLS-inspecting proxy cert, even though `curl` and Windows do — worked around with the `truststore` package (`truststore.inject_into_ssl()`) to use the Windows system cert store instead. Full request/response logged to `results/spike_04_llm_call.json` with the API key redacted. |
| `05_e2e.py` | GREEN | Full ingest → embed → store → retrieve (top-3) → LLM-derive → store → edge pipeline, using a small 4-document corpus with one embedded false claim ("Eiffel Tower is in Berlin"). The injected memory was correctly retrieved as a top-3 parent, and the LLM's derived summary preserved the `Berlin` marker token but explicitly flagged it as incorrect ("is incorrectly noted to be located in Berlin") rather than asserting it as fact — a real REFERENCES-not-CARRIES boundary case, not an invented one. Full trace logged to `results/spike_05_e2e.json`. |
| `06_prefix_property.py` | GREEN | Tests the load-bearing claim behind `configs/experiment_grid.yaml`'s generation/analysis split: a depth-5 trace's depth-d prefix (d=0..4) must equal a trace generated with `max_depth=d` directly. Uses a deterministic mock derivation function (no live LLM) so results reflect harness/bookkeeping correctness, not model nondeterminism. Result: **PREFIX_SAFE** on the honest append-only harness design (all d=0..4 pass, plus a differential check confirming `max_depth` never leaks into prompt/query text). A deliberate negative-control variant (a later-depth operation mutating an earlier-depth memory — the specific failure case flagged in review) correctly **fails** at d=2/d=3, proving the check can actually detect a real violation rather than passing vacuously. **Caveat, stated in the script's own output: this validates the design, not the eventual real `eval/` harness** — a real implementation could still violate the property (non-deterministic write ordering, an update-in-place bug) even though this mock's append-only design doesn't; re-run an equivalent check against the real harness once it exists. |

## Environment

- Docker container: `memoryir-pg` (`pgvector/pgvector:pg16`), `postgresql://postgres:memoryir@localhost:5433/memoryir`
- This container is a local dev convenience, not committed anywhere — anyone re-running these spikes needs to `docker run` it themselves (see command in git history / ask for it to be added to a `docker-compose.yml` if this becomes a recurring need past week 1).
- Python 3.10.7, `psycopg[binary]` 3.2.9, `pgvector` (Python) 0.5.0, `sentence-transformers` 4.1.0, `openai` 1.63.0, `truststore` (installed to work around the TLS issue below)
- LLM/embedding credentials: `../creds.env` (one directory above the repo root, gitignored) — Azure OpenAI endpoint + `gpt-4o-mini` deployment used for 04/05.

## Known issues to fix before real runs (not just spikes)

1. **TLS inspection breaks Python's default cert verification** on this
   network. `truststore.inject_into_ssl()` is a workable fix but needs to be
   applied consistently everywhere `eval/` makes HTTP calls, not just in
   spike scripts — worth centralizing in `src/memoryir/` rather than
   repeating per-script.
2. **`02_embed.py`'s model is a placeholder.** The real embedding model
   needs to be pinned (Azure has an embedding deployment in `creds.env` —
   `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` — that was not used here since the
   local model was already working; worth switching to it for consistency
   with the LLM calls, or deciding deliberately to keep them separate).
3. **`psycopg`/`pgvector`-python needs explicit `::vector` casts** on query
   parameters — noted in the `01_db.py` row above, applies everywhere
   vectors get passed as query params.
