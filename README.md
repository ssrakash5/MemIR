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

Pre-registration STAMPED 2026-08-12 (`docs/preregistration.md`). Full
generation + labeling pipeline complete across 3 models
(gpt-4o-mini, gpt-4o, Llama-3.3-70B-Instruct), 30 scenarios (24 poisoned
+ 6 clean controls), H1–H4 all computed with bootstrap CIs against the
full corpus — see `docs/corpus_card.md` for corpus statistics and
`docs/paper/` for the in-progress draft (intro/related work/threat
model/method/limitations drafted; results section pending final
clean-control numbers). `CLAUDE.md` has agent-facing standing context
and the frozen-artifacts list.

## Layout

- `docs/` — prior art, positioning, labeling protocol, pre-registration,
  corpus card, paper drafts (`docs/paper/`)
- `src/memoryir/` — core library (db, embeddings, harness, labeler,
  metrics, scenarios)
- `spike/` — throwaway infra-verification scripts (not product code)
- `eval/` — generation/labeling/metrics runners (`run_full_sweep.py`,
  `label_full_corpus.py`, `compute_metrics.py`, `compute_h2/h3/h4_metrics.py`)
- `tests/` — fixture tests (metrics validated against known answers
  before touching real data)
- `configs/` — experiment grid (dated decisions recorded inline) and
  scenario specs
- `results/` — experiment outputs (git-ignored except curated summaries
  like `results/kappa_sample/`)
