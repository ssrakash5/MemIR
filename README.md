# MemoryIR

Provenance-based exposure tracing for poisoned agent memory. Research artifact
for IEEE SaTML 2027 (submission deadline 2026-09-29).

## Research question

How does the precision of provenance-based exposure flagging degrade as a
function of derivation depth and retrieval fan-out, and what precision/recall
frontier is achievable when conservative propagation is relaxed with
similarity and rank thresholds?

## Status

Week 1 (2026-08-10 – 2026-08-16): design and de-risking only. See
`week1_execution_plan.md` at the repo root's parent directory for the current
plan, `CLAUDE.md` for agent-facing standing context, and `docs/` for the
research design documents as they land.

## Layout

- `docs/` — prior art, positioning, labeling protocol, pre-registration
- `src/memoryir/` — core library (db, embeddings, provenance, lineage)
- `spike/` — throwaway infra-verification scripts (not product code)
- `eval/` — experiment harness (week 2+)
- `configs/` — experiment grid and run configs
- `results/` — experiment outputs (git-ignored except summaries)
