# Data Validation

Checklist run against the completed corpus (21,570/21,600 traces,
216,319 labeled memories, 3 models, 30 scenarios).

## 1. Every cell has expected N

Confirmed via `sweep_runs` (the generation checkpoint table): every
enumerated `(scenario_id, model, top_k, write_fanout,
derivation_transform, seed)` cell has exactly one row, `done` or
`error_exhausted`, no duplicates, no gaps — verified by the
enumeration-vs-database reconciliation run at the end of the original
generation pass (0 missing, 0 duplicate, 0 extra keys) and re-confirmed
after the clean-control extension (21,600 enumerated = 21,570 done +
30 error_exhausted).

## 2. No silent model-version drift mid-run

Every generation call logs its model/deployment name alongside the
response (`results/full_sweep_llm_log/`). Deployment names
(`gpt-4o-mini`, `gpt-4o`, `Llama-3.3-70B-Instruct`) and API versions
were read from a single `creds.env` file, unchanged for the duration of
both generation runs (2026-08-12 through 2026-08-15/16) — no
deployment string ever varied within a run. This confirms *our*
requests didn't drift; it does not and cannot rule out Azure silently
updating the model behind a fixed deployment alias server-side, which
is outside what any client-side log can detect.

## 3. Failure rate, quantified

- **30 / 21,600 (0.139%) generation cells permanently failed**
  — all Llama-3.3-70B-Instruct, all Azure content-safety filter
  rejections (`finish_reason: content_filter`, label `Jailbreak`),
  concentrated in `authoritative_framing` scenarios at
  `write_fanout=3`. Confirmed non-deterministic-but-mostly-persistent
  (a retry pass recovered 95 of an original 183 flagged failures before
  these 30 stabilized at `attempts=5`). Not imputed — reported as
  missing data (`docs/corpus_card.md`, `docs/paper/limitations.md`).
- **Labeling: 0 failures** across 173,119 + 43,200 = 216,319 calls.

## 4. Seeds actually differ — a real, non-obvious finding

A seeding bug producing identical runs across nominally-different seeds
is a classic and easy-to-miss failure mode, so we checked directly: for
every
`(scenario, model, top_k, write_fanout, derivation_transform)` cell's 5
seeds, do they produce distinct `child_1` (depth 1) content?

| | Rate |
|---|---|
| All 5 seeds byte-identical | 39.5% (1,708 / 4,320 cells) |
| All 5 seeds distinct | 8.8% (381 / 4,320 cells) |
| Partial diversity (2–4 unique) | 51.6% (2,231 / 4,320 cells) |

This is **not a seeding bug** — no `seed` parameter is ever sent to any
model API (a deliberate choice, see `configs/experiment_grid.yaml`'s
seed-resolution note: seeds rely on genuine API-level stochasticity at
`temperature=0`, not a request-level seed, since passing one would
defeat the noise-reduction purpose seeds were added for). But the rate
of full duplication is high enough to state plainly rather than assume
away, and it is **not uniform** — it varies by exactly the factors
you'd expect if it reflects genuine task determinism rather than a
pipeline defect:

**By derivation_transform** (all-5-identical rate): `summarize` 60.6%,
`refine` 42.5%, `paraphrase` 38.3%, `continue` 16.8% — a short,
compressive task (`summarize`) converges to a canonical output far more
often than an open-ended one (`continue`), exactly the pattern a real
determinism effect (not a bug) should produce.

**By model** (all-5-identical rate): gpt-4o-mini 45.0%, llama-3.3-70b
46.3%, gpt-4o 27.3% — gpt-4o shows meaningfully more run-to-run
diversity at `temperature=0` than the other two, consistent with the
kappa-validation non-determinism finding (`docs/labeling_protocol.md`)
that `temperature=0` does not guarantee bit-identical output on Azure.

**Implication, stated honestly:** the 3→5 seed decision's stated
justification (within-scenario noise reduction from confirmed API
non-determinism) holds, but unevenly — for `summarize`-heavy or
gpt-4o-mini/llama cells, 5 seeds often buy closer to 2–3 effectively
distinct realizations, not 5. This does **not** change the frozen
statistical design: the bootstrap resampling unit was always
`scenario_id` (n=24), never seed count, so this finding doesn't reduce
statistical power relative to what was ever claimed — but it is worth
stating in the paper's limitations/data-validation section rather than
letting a reviewer discover it independently.
</content>
