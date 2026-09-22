# eval/ — full pipeline

21,570/21,600 traces generated, 216,319 memories labeled, H1–H4
computed with bootstrap CIs, across 3 models and 30 scenarios (24
poisoned + 6 clean controls). The scoped v1 harness described lower in
this file (`eval/run.py`) is retained for quick smoke tests but is not
the production path — `eval/run_full_sweep.py` is.

## Reproduction order

Requires: `memoryir-pg` Docker container running, `../creds.env`
present (Azure OpenAI + Azure AI Foundry credentials — see
`src/memoryir/llm.py` for exact env vars), `pip install -e ".[eval]"`.

```bash
# 1. Sanity-check the enumeration before touching the DB/API (no cost)
python eval/run_full_sweep.py --dry-run

# 2. Generate (resumable -- safe to re-run after a crash/kill; only
#    processes trace keys not already 'done'). Detach from the shell if
#    running for hours -- see docs/data_validation.md for what a launch
#    looks like end to end, including retry-to-exhaustion behavior.
python eval/run_full_sweep.py --launch --workers 3 --max-attempts 5

# 3. Label every derived memory against its scenario's semantic_target
#    (frozen pipeline, src/memoryir/labeler.py -- unchanged since the
#    kappa=0.8699/0.8838 validation, see docs/labeling_protocol.md)
python eval/label_full_corpus.py --launch --workers 3

# 4. Compute H1 (structural vs context_exposure) + fixture-validate first
python -m pytest tests/test_metrics.py -q   # or: python tests/test_metrics.py
python eval/compute_metrics.py
python eval/bootstrap_h1.py

# 5. Compute H2 (attribution threshold), H3 (laundering), H4 (containment)
python eval/compute_h2_metrics.py
python eval/compute_h3_metrics.py
python eval/compute_h4_metrics.py
python eval/bootstrap_h2_h3_h4.py

# 6. Clean-control false-positive baseline
python eval/compute_clean_control_metrics.py

# 7. Figures (regenerable by one command, no hand-edited plots)
python eval/make_figures.py
```

Every step is idempotent/resumable and reads only from Postgres +
`configs/` — no hidden state. Raw + summary CSVs land in
`results/metrics/` (git-ignored, regenerable); figures land in
`results/figures/`.

## What `run_full_sweep.py` does (the real generation harness)

For each enumerated `(scenario_id, model, top_k, write_fanout,
derivation_transform, seed)` cell, `generate_trace()`
(`src/memoryir/harness.py`) runs:

1. **Depth 0** — every scenario `source_fact` and `distractor_pool`
   entry is inserted as a memory row.
2. **Depth 1** — the frozen "shared retrieval per run" model: all of a
   scenario's source facts are retrieved together, distractors filling
   the rest of `top_k`, true-parents-ranked-first. `child_1`/`child_2`/
   `child_3` (when `write_fanout=3`) are all derived from this same
   shared context, but each LLM call gets a `focus_texts`/
   `background_texts` split so a write is actually about its own true
   parent, not a blend of everything retrieved. `child_3` has no
   scenario-authored parent — treated as a distractor-only sibling at
   every depth (an explicit, dated 2026-08-12 decision, see
   `src/memoryir/harness.py`'s module docstring).
3. **Depths 2–5** — the depth-continuation rule: `child_1`'s lineage
   continues, sibling writes are fresh distractor-seeded writes each
   depth.

Every derived memory's oracle `STRUCTURAL_PARENT`/`CO_RETRIEVED` edges
are recorded straight from the scenario spec's approved `true_parents`
— no inference, no LLM judgment of causation. Checkpointing is via the
`sweep_runs` Postgres table (`src/memoryir/db.py`): claim-and-retry is
atomic, a crash mid-trace wipes and regenerates that one trace's rows
(idempotent), never duplicates or silently skips.

## Multi-model support

Three backends implement an identical `derive()` interface
(`make_llm_client()` in `src/memoryir/llm.py`) so the harness is
agnostic to which model produced a trace: `LLMClient` (gpt-4o-mini,
gpt-4o — same Azure OpenAI resource/API shape) and `LlamaClient`
(Llama-3.3-70B-Instruct — a distinct Azure AI Foundry REST API).
gpt-4o-mini's original 5,760-trace corpus (generated before the model
factor existed) keeps its original no-model-segment trace-ID format
specifically so re-enumeration recognizes it as already-done rather
than regenerating it — see `src/memoryir/sweep_grid.py`'s
`trace_key()`.

## Known, documented gaps (not blocking, see docs/paper/limitations.md)

- 30/21,600 traces (Llama-3.3-70B-Instruct only) permanently missing —
  Azure content-safety filter (`Jailbreak` label), not a code defect.
- `embedding_model` is still the placeholder `all-MiniLM-L6-v2`, not a
  finally-pinned choice.
- H2's attribution score (cosine similarity) and H4's `depth_aware`
  algorithm are both explicit, dated post-hoc operationalizations of
  underspecified factors in the original design — see
  `docs/preregistration.md`'s H2/H4 sections.

## eval/run.py — the original scoped v1 harness (retained for smoke tests)

Runs a small subset (2 transforms, fixed `top_k`/`write_fanout`, one
seed) for quick sanity checks without touching the full grid:

```bash
python eval/run.py                                    # defaults: transforms=[summarize, paraphrase], top_k=5, write_fanout=2, max_depth=5, seed=0
python eval/run.py --transforms summarize paraphrase refine continue --top-k 10
```

This is what originally built the labeling-validation corpus (48
traces) that the κ=0.8699/0.8838 validation ran against — it predates
`write_fanout=3` support and the multi-model extension, so it only ever
exercises `write_fanout ∈ {1,2}` and gpt-4o-mini. Left untouched
deliberately (see `src/memoryir/harness.py`'s `generate_trace()`
`trace_id` override parameter) so it keeps working exactly as it did
during that validation, not because it's still the recommended path for
new work.
</content>
