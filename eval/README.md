# eval/ — generation harness (v1, scoped to labeling validation)

**Scope note (see `CLAUDE.md` "Current phase"):** this harness exists to
unblock pre-registration's two real remaining blockers — the labeling
protocol's 9 missing worked examples and the 100–150-memory κ validation
— by producing real derived-memory output under the frozen scenario/
oracle rules. It runs the 24 approved scenarios (`configs/scenarios/`)
through a small number of `derivation_transform` values at fixed
`top_k`/`write_fanout`, not the full 3,456-trace production sweep across
`configs/experiment_grid.yaml`'s `generation_factors`. That sweep is a
separate, later task, still gated on κ passing.

## Usage

```bash
python eval/run.py                                    # defaults: transforms=[summarize, paraphrase], top_k=5, write_fanout=2, max_depth=5, seed=0
python eval/run.py --transforms summarize paraphrase refine continue --top-k 10
```

Requires:
- `memoryir-pg` Docker container running (`docker ps --filter name=memoryir-pg`)
- `../creds.env` present (one directory above the repo root) with Azure
  OpenAI credentials — see `spike/04_llm.py` for the exact env vars used
- `pip install -e ".[eval]"` (or the individual packages: `sentence-transformers`,
  `openai`, `truststore`, `python-dotenv`, on top of the base dependencies)

## What it does

For each `(scenario, derivation_transform)` pair, `generate_trace()`
(`src/memoryir/harness.py`) runs:

1. **Depth 0** — every scenario `source_fact` (P1/B1/B2) and every
   `distractor_pool` entry is inserted as a memory row.
2. **Depth 1** — per the frozen "shared retrieval per run" model: ALL of
   a scenario's source facts are retrieved together (since `child_2`
   needs its own true parent, e.g. B2, retrievable in the same run as
   `child_1`'s), with distractors filling the rest of `top_k`. Both
   `child_1` and `child_2` are derived from this same shared context,
   but the LLM call is given a `focus_texts`/`background_texts` split
   (see below) so each child is actually about its own true parent, not
   a blend of everything retrieved.
3. **Depths 2–5** — the frozen depth-continuation rule: `child_1`'s
   lineage continues (previous depth's `child_1` is the sole true
   parent), `child_2`-style siblings are fresh each depth, seeded from
   `distractor_pool[(depth-2) % 9]` (cycling through the pool rather than
   inventing new content or calling the LLM for free-form generation —
   reuses distractor text already checked for topical/lexical
   cleanliness during scenario review).

Every derived memory gets its oracle `STRUCTURAL_PARENT`/`CO_RETRIEVED`
edges recorded in `memory_influence`, straight from the scenario spec's
approved `true_parents` (depth 1) or the continuation rule (depth 2+) —
no inference, no LLM judgment of causation.

## The focus/background prompt design (a real bug found and fixed during v1 build)

The first smoke test revealed that giving the LLM a generic "summarize
everything retrieved" instruction, with the full shared context and no
signal about which item to focus on, made `child_2` (supposed to be a
clean sibling derived only from e.g. B2) blend in the poisoned P1 content
anyway — because the model had no reason to ignore it. That would have
made every `child_2` in the corpus spuriously contaminated, useless for
building genuine `COEXPOSED`/"clean sibling" labeling examples.

Fixed by splitting `LLMClient.derive()`'s context into `focus_texts`
(this write's actual true parents) and `background_texts` (everything
else retrieved into the same shared context, shown but explicitly marked
off-topic). This mirrors a real agent that retrieves N items in one
query but writes a focused note about a specific one. Verified in the
smoke test: `child_2` at depth 1 now correctly derives only from B2's
formatting-standard content, `child_1` only from P1's poison, both
sharing the same retrieved context per the oracle bookkeeping.

## Known limitations of this v1 (not blocking, but real)

- Only `top_k=5`/`write_fanout=2` exercised so far — the frozen
  distractor-count formula (`max(0, top_k - true_parent_count)`) hasn't
  been tested at other `top_k` values yet.
- Depth-2+ distractor fill always starts from `distractor_pool[0]`
  (skipping the seed), so the same distractors tend to recur across
  depths within a trace — fine for this scope, would want more variety
  for the full production sweep.
- No `write_fanout=3` support yet (harness only handles 1 or 2 children
  per run).
- `embedding_model` is still the spike placeholder (`all-MiniLM-L6-v2`),
  not whatever gets pinned in `configs/experiment_grid.yaml`.

## Output

Derived memories land in Postgres (`memories`/`memory_influence` tables,
`src/memoryir/db.py`). Full LLM request/response logs (API key never
included) go to `results/eval_llm_log/call_NNNNN.json`. Query the DB
directly to pull examples for `docs/labeling_protocol.md`'s worked
examples or to draw the κ validation sample — no separate export step
exists yet.
