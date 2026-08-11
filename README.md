# MemoryIR

Post-incident blast-radius reconstruction for poisoned agent memory. Research
artifact for IEEE SaTML 2027 (submission deadline 2026-09-29).

## Research question

Once a memory or source is known to be compromised, how accurately can
execution provenance reconstruct the downstream blast radius in a branching
agent-memory graph, and what does containment cost, as a function of
retrieval fan-out, derivation depth, and attribution policy?

(Revised 2026-08-11 — see `docs/positioning.md` for why the original
precision-of-exposure-flagging framing failed the Tuesday positioning gate
and how this question was arrived at.)

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
