# Pre-registration

**Status: skeleton draft, NOT the committed pre-registration.** Updated
2026-08-11 (second revision, same day) to match the finalized
generation/analysis split in `configs/experiment_grid.yaml`: `depth` and
`attribution_threshold` are analysis-time factors computed post-hoc from a
persisted execution trace, not separate generation runs. Still not ready to
gate data generation: κ validation hasn't run, oracle-authoring method is
undecided, and the scenario_id/pseudo-replication question below is still
open. **Do not generate experiment data against this version.**

---

## 1. Hypotheses (unchanged from the first 2026-08-11 revision)

- **H1 — Blast-radius inflation.** Conservative provenance (`attribution_threshold=null`)
  has high blast-radius recall (R_BR) but suffers superlinear blast-radius
  inflation (\|B_flagged\|/\|B_true\|) as retrieval fan-out (`top_k`) and
  write fan-out (`write_fanout`) grow.
- **H2 — Precision/recall frontier shifts with depth.** Attribution
  thresholds reduce inflation but reduce recall, and this P_BR/R_BR
  frontier shifts with derivation depth. Report as a frontier, not a
  collapsed "best threshold" scalar — see marginalization rule below.
- **H3 — Execution provenance outlasts surface traceability.** Surface-level
  (marker-token) traceability degrades faster with `derivation_transform`
  strength than execution-provenance (oracle-based) traceability does.
  Operationalized via the `TRUE_DESCENDANT + CLEAN` oracle/content-label
  intersection in `docs/labeling_protocol.md` — this is the precise
  definition of "laundered," replacing the earlier `CARRIES == true AND
  markers absent` definition, which conflated the content-label and
  oracle-label layers.
- **H4 — Depth-aware containment reduces over-quarantine.** The
  `depth_aware` containment policy substantially reduces unnecessary
  quarantine relative to `flat_transitive`, measured via containment cost
  (C_regen, defined below), while preserving high action-level containment
  recall. `containment_policy` is a post-hoc analysis factor, not a new
  generation axis.

## 2. Variables

See `configs/experiment_grid.yaml` for the authoritative, finalized
generation/analysis split.

- **Generation factors** (each combination produces one real trace —
  expensive): `top_k` {1,3,5,10}, `write_fanout` {1,2,3}, `injection_style`
  (4 values), `derivation_transform` (4 values, matching MemLineage §5.3's
  summarize/paraphrase/refine/continue vocabulary), `prompt_style`
  (terse/verbose/structured — renamed from `summarization_prompt`),
  `seeds` {0,1,2}. **1,728 generated traces.**
- **Analysis factors** (computed post-hoc from a trace's persisted
  `(parent, child, attribution_score, run_id)` edges, no re-generation
  needed): `depth` {0..5}, `attribution_threshold` {null, 0.5, 0.7, 0.85},
  `containment_policy` {flat_transitive, depth_aware}. **41,472 depth ×
  threshold analysis cells** derivable from the 1,728 traces; containment
  policy is a further analysis layer on top of that.
- **Generation controls:** `max_depth=5` as a hard external harness stop
  condition NOT exposed to the agent's prompt (so a depth-d prefix of a
  depth-5 trace is a valid depth-d trace on its own — the "prefix
  property" this whole split depends on). Model, embedding model, corpus
  size — still `TBD`.
- **Benchmark-design requirement (not a variable, a construction rule):**
  every generation run's retrieved context must mix true parents
  (`STRUCTURAL_PARENT`, per the oracle schema in
  `docs/labeling_protocol.md`) with co-retrieved distractors
  (`CO_RETRIEVED`). Without this, conservative provenance has perfect
  precision by construction and the paper's central phenomenon can't
  appear in the data.

## 3. Labeling protocol

See `docs/labeling_protocol.md`, now with two independent label layers:
content-level (CARRIES/REFERENCES/CLEAN, via the automated 3-signal
labeler) and oracle/structural (`STRUCTURAL_PARENT`/`CO_RETRIEVED` edges,
`COMPROMISED_ROOT`/`TRUE_DESCENDANT`/`COEXPOSED`/`UNRELATED` nodes, set at
corpus-construction time). **Two things not yet decided, both blocking:**
(a) whether oracle labels get hand-authored per scenario or generated
programmatically with spot-checking, and (b) whether the κ validation
needs to be run separately against each label layer (content-label
agreement vs. a separate check that the corpus's claimed oracle structure
holds up under inspection).

## 4. Sample sizes

**Not yet determined**, pending:
- The distractor-per-run design (how many true parents vs. distractors per
  retrieval — this directly sets how hard the precision problem is, so it
  needs to be a deliberate choice, not incidental).
- **Pseudo-replication check (new, from second review):** if each
  `injection_style` corresponds to one hand-written payload and the 3
  seeds just regenerate that same scenario under model stochasticity, the
  seeds tell us nothing about generalization across independently
  constructed attack instances of that style. Either the corpus supplies
  multiple independently constructed `scenario_id`s per `injection_style`
  (preferred — bootstrap CIs over `scenario_id`, not over factorial
  cells), or this must be stated as an explicit limitation. **Currently
  undecided** — `configs/experiment_grid.yaml` flags this as
  `scenario_id_status: UNDECIDED`. This has to be resolved before sample
  sizes can be set, since "how many scenarios per style" is itself a
  sample-size question.
- Target scale from `docs/labeling_protocol.md`: ≥200 injection instances
  across ≥4 styles, chains to depth ≥3 — a floor for the labeling
  validation corpus specifically, not necessarily the generation-run count.

## 5. Statistics

- Paired bootstrap, 10,000 resamples, for all point estimates.
- 95% confidence intervals on every reported number.
- Wilcoxon signed-rank test for paired comparisons.
- **Bootstrap resampling unit is `scenario_id` once that axis exists (see
  §4), not raw factorial cells** — otherwise seeds within one hand-written
  scenario would be pseudo-replicated into the CI.
- **Marginalization rule (preregistered estimand — balanced marginal
  means over the experimental distribution we defined, NOT real-world
  deployment prevalence):** average seeds within each cell first, then
  give every level of a marginalized factor equal weight regardless of
  cell count underneath it. Per-hypothesis marginalization plan is spelled
  out in `configs/experiment_grid.yaml`'s trailing comment block — H1
  holds top_k×write_fanout×depth explicit at `attribution_threshold=null`;
  H2 holds attribution_threshold×depth×top_k×write_fanout explicit and
  reports a frontier; H3 holds derivation_transform×depth explicit at
  `attribution_threshold=null`; H4 applies containment_policy post-hoc to
  every reconstructed graph. All four marginalize equally over whichever
  generation factors aren't held explicit.
- **depth=0 special case:** at depth 0 the compromised root may have zero
  downstream descendants, giving \|B_true\|=0 and making R_BR/inflation
  undefined. **Do not coerce to zero.** Report P_BR/R_BR/inflation as N/A
  at any horizon where the oracle downstream blast radius is empty; depth
  0 is still analyzed for the surface-marker baseline and harness
  validation.

## 6. Falsification conditions (unchanged from the first revision)

Stated in advance, to be reported regardless of outcome:

- **If blast-radius inflation stays near 1.0× across the tested fan-out
  range**, the over-tainting problem motivating this paper doesn't
  materialize in practice and the premise is wrong.
- **If depth-aware containment (H4) doesn't measurably reduce over-
  quarantine relative to flat transitive taint**, the paper's proposed
  remedy has no advantage over the naive baseline.
- **If execution-provenance recall degrades at the same rate as surface
  traceability (H3 null)**, the case for provenance over simpler
  content-matching approaches weakens substantially.

## Metric definitions (canonical — supersedes earlier E_* notation)

Set notation over blast-radius **objects**, not edges (edges get a
separate P_E/R_E pair — see below; conflating the two was an error in the
first 2026-08-11 revision):

- Blast-radius precision: P_BR = \|B_flagged ∩ B_true\| / \|B_flagged\|
- Blast-radius recall: R_BR = \|B_flagged ∩ B_true\| / \|B_true\|
- Inflation ratio: \|B_flagged\| / \|B_true\|
- Containment cost: C_regen = count of unique *generating runs* that must
  be replayed to regenerate the quarantined set — not per-object cost (one
  run producing 3 exposed memories is 1 replay, not 3). Secondary:
  regeneration_tokens if logged. Normalized H4 metric: Regeneration
  Overhead = C_predicted / C_oracle.
- Attribution edge quality: P_E, R_E — precision/recall of inferred
  `(parent, child)` edges against the oracle's `STRUCTURAL_PARENT` vs.
  `CO_RETRIEVED` labels. Distinct question from blast-radius reconstruction
  (did we infer the right edges vs. did we reconstruct the right exposed
  set) — report separately, do not collapse into one number.

## Before this can be committed as the real pre-registration

1. ~~Positioning correction~~ — done 2026-08-11.
2. ~~Generation/analysis split, 41,472-cell arithmetic correction,
   distractor requirement~~ — done 2026-08-11 (this revision).
3. `docs/labeling_protocol.md` needs: κ validation run and passed (against
   both label layers — undecided how), remaining 9 worked examples, and
   the oracle-authoring method decided (hand vs. programmatic).
4. `scenario_id`/pseudo-replication question (§4/§5 above) needs a
   decision — this determines whether current sample-size thinking is even
   valid.
5. Sample sizes need to be set once §3/§4 resolve.
6. Once 3–5 are done, re-commit with a note marking it as the actual
   pre-registration timestamp; no data generation before that commit.
