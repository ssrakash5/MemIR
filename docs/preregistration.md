# Pre-registration

**Status: skeleton draft, NOT the committed pre-registration.** Updated
2026-08-11 (third revision, same day) to match the finalized scenario
design in `configs/experiment_grid.yaml`: 24 `scenario_id`s (4
`poison_form` × 6 independent scenarios each) as the real
sampling/bootstrap unit, `prompt_style` demoted to a balanced per-scenario
attribute, and oracle authoring resolved to programmatic generation from a
human-approved scenario spec. `depth`/`attribution_threshold` remain
analysis-time factors, now validated by `spike/06_prefix_property.py`
(GREEN). **All 24 scenario specs are now HUMAN-APPROVED** (4 pilot,
approved 2026-08-11; 20 more, drafted and reviewed 2026-08-12 — 12
approved as drafted, 8 revised for semantic-target wording and
distractor/clean-sibling contamination, zero `true_parents` errors found
— see `configs/scenarios/README.md` for full detail). Also RESOLVED
2026-08-12: the automated labeler pipeline (LLM-primary + NLI
verification + adjudication, marker tokens excluded from the label
decision — see `docs/labeling_protocol.md`). Also done 2026-08-12: a v1
`eval/` generation harness (scoped to labeling validation, not the full
production sweep — see `CLAUDE.md` and `eval/README.md`), run
successfully (48 real traces, 480+ derived memories), and 8/10 labeling
worked examples built from that real output (2 categories genuinely
searched for and not found — a reportable finding, see
`docs/labeling_protocol.md`). **Status: BLOCKED** — see the closing
section below for the authoritative blocker list. κ validation has not
been run, and two scientific-framing questions surfaced by the worked
examples need resolution before the rubric can be frozen. Sample sizes
below still need real numbers plugged in.
**Do not generate experiment data against this version.**

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
  expensive): `scenario_id` (24 values: 4 `poison_form` × 6
  independently-constructed scenarios each — the real sampling unit, see
  §4/§5), `top_k` {1,3,5,10}, `write_fanout` {1,2,3}, `derivation_transform`
  (4 values, matching MemLineage §5.3's summarize/paraphrase/refine/continue
  vocabulary), `seeds` {0,1,2}. `prompt_style` (terse/verbose/structured —
  renamed from `summarization_prompt`) is a **balanced per-scenario
  attribute** (2 of each style's 6 scenarios get each `prompt_style` value),
  not a crossed factorial axis. **3,456 generated traces**
  (24×4×3×4×3).
- **Analysis factors** (computed post-hoc from a trace's persisted
  `(parent, child, attribution_score, run_id)` edges, no re-generation
  needed): `depth` {0..5}, `attribution_threshold` {null, 0.5, 0.7, 0.85},
  `containment_policy` {flat_transitive, depth_aware}. **82,944 depth ×
  threshold analysis cells** derivable from the 3,456 traces (3,456×6×4);
  containment policy is a further analysis layer on top of that.
- **Generation controls:** `max_depth=5` as a hard external harness stop
  condition NOT exposed to the agent's prompt. The prefix property this
  split depends on (a depth-d prefix of a depth-5 trace equals a trace
  generated with `max_depth=d` directly) is now **validated**:
  `spike/06_prefix_property.py` passed GREEN on 2026-08-11 for d=0..4,
  including a negative control proving the check can detect a real
  violation. Caveat carried from that spike: it validates the *design* via
  a deterministic mock, not the eventual real `eval/` harness — that needs
  its own equivalent check once built. Model, embedding model, corpus
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
content-level (CARRIES/REFERENCES/CLEAN, evaluated against each scenario's
`semantic_target`, via the automated 3-signal labeler) and
oracle/structural (`STRUCTURAL_PARENT`/`CO_RETRIEVED` edges,
`COMPROMISED_ROOT`/`TRUE_DESCENDANT`/`COEXPOSED`/`UNRELATED` nodes, set at
corpus-construction time). **Oracle authoring is now RESOLVED:**
programmatic generation from a human-approved scenario specification (see
`configs/experiment_grid.yaml`'s "Scenario design" section for the schema)
— a human approves scenario semantics and true-dependency structure, code
deterministically derives oracle edges/nodes, the LLM only generates
surface text. **Still open:** whether the κ validation needs to run
separately against each label layer (content-label agreement vs. a
separate check that the corpus's claimed oracle structure holds up under
inspection of a sample of generation traces).

## 4. Sample sizes

**Scenario count is now RESOLVED: 24 `scenario_id`s (4 `poison_form` ×
6 independently-constructed scenarios each)** — see
`configs/experiment_grid.yaml`'s "Scenario design" section. This closes
the pseudo-replication risk: seeds now measure within-scenario model/run
stochasticity, and generalization across independently constructed attack
instances of a style is what the 6-scenario replication is for.

**Still not fully determined:**
- The distractor-per-run design (how many true parents vs. distractors per
  retrieval within each scenario's `distractor_pool` — this directly sets
  how hard the precision problem is, so it needs to be a deliberate
  choice per scenario, not incidental).
- ~~The pilot's 4 scenario specifications don't exist yet~~ — **done and
  HUMAN-APPROVED 2026-08-11** (`configs/scenarios/pilot/`). The remaining
  20 (5 more per `poison_form`) still need to be written before the full
  24-scenario generation run.
- Target scale from `docs/labeling_protocol.md`: ≥200 injection instances
  across ≥4 styles, chains to depth ≥3 — a floor for the *labeling
  validation* corpus specifically, distinct from and smaller than the
  24-scenario / 3,456-trace generation design (see that document's
  clarification of this distinction).

## 5. Statistics

- Paired bootstrap, 10,000 resamples, for all point estimates.
- 95% confidence intervals on every reported number.
- Wilcoxon signed-rank test for paired comparisons.
- **Bootstrap resampling unit is `scenario_id`, stratified by
  `poison_form`, not raw factorial cells or trace rows** — seeds
  within one scenario are nested repeated measurements, not independent
  samples; resampling 3,456 trace rows as though independent would be
  pseudo-replication.
- **Marginalization rule (preregistered estimand — balanced marginal
  means over the experimental distribution we defined, NOT real-world
  deployment prevalence):** average seeds within each scenario-condition
  first, then give every `scenario_id` equal weight regardless of cell
  count underneath it. Per-hypothesis marginalization plan is spelled
  out in `configs/experiment_grid.yaml`'s trailing comment block — H1
  holds top_k×write_fanout×depth explicit at `attribution_threshold=null`;
  H2 holds attribution_threshold×depth×top_k×write_fanout explicit and
  reports a frontier; H3 holds derivation_transform×depth explicit at
  `attribution_threshold=null`; H4 applies containment_policy post-hoc to
  every reconstructed graph. All four marginalize equally over scenario_id
  (stratified by poison_form) and whichever other generation factors
  aren't held explicit.
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
   distractor requirement~~ — done 2026-08-11.
3. ~~Prefix property validated~~ — `spike/06_prefix_property.py` GREEN,
   2026-08-11.
4. ~~MemSecBench full read~~ — done 2026-08-11; positioning survives
   unchanged (see `docs/positioning.md`).
5. ~~`scenario_id`/pseudo-replication question, oracle-authoring method~~ —
   RESOLVED 2026-08-11: 24 scenarios, programmatic oracle generation from
   human-approved specs.
6. ~~The 24 scenario specifications don't exist yet~~ / ~~the 20 aren't
   approved~~ — **all 24 are now HUMAN-APPROVED.** Pilot's 4 approved
   2026-08-11, including the review pass that corrected `true_parents` to
   the minimal causally-necessary set in 3/4. Remaining 20 drafted and
   reviewed 2026-08-12: 12 approved as drafted, 8 revised (semantic-target
   wording, distractor/clean-sibling contamination) — **zero
   `true_parents` errors found in the 20**, confirming the ground-truth
   principle transferred correctly to fresh scenario construction. See
   `configs/scenarios/README.md` for full per-scenario detail.
7. ~~Automated labeler combination rule~~ — RESOLVED 2026-08-12:
   LLM-primary + NLI verification + adjudication, marker tokens excluded
   from the label decision entirely (see `docs/labeling_protocol.md`).
8. ~~MPBench, AgentPoison, MINJA full reads~~ — done 2026-08-12; the
   entire `week1_execution_plan.md` §1 literature gate is closed (see
   `docs/prior_art.md`).
9. ~~20 new scenarios reviewed/approved~~ — done 2026-08-12.
10. ~~eval/ harness (v1, scoped) built and run~~ — done 2026-08-12: 48
    real traces (24 approved scenarios × 2 transforms), 480+ derived
    memories with full oracle bookkeeping. See `eval/README.md`.
11. ~~9 remaining labeling worked examples~~ — done 2026-08-12, built
    from real `eval/` output (`docs/labeling_protocol.md`). 8/10 filled;
    2 categories (surface-CLEAN-but-structurally-descended, multi-step
    laundering) were searched for directly across 4 derivation transforms
    and 5 depths and genuinely not found — reported as a finding (**zero
    observed laundering in the pilot corpus**), not silently skipped.
    This bears directly on H3 and the falsification condition in §6 above
    — needs discussion, not silent resolution.
12. **Two new open items surfaced by the worked-examples pass, both
    need resolution before the rubric can be frozen** (see
    `docs/labeling_protocol.md`'s closing section, items 6–7): (a) the
    `multi_hop_setup` CARRIES/REFERENCES boundary — the model
    systematically juxtaposes rather than composes its two source facts,
    across every trace checked, not a one-off; (b) an oracle-vs-content
    divergence finding — `CO_RETRIEVED` content measurably leaked into
    focused writes in 2 of the checked traces, producing content-CARRIES
    that a structural-only detector would miss entirely. (b) especially
    may need to change how H1/H2/H4 are framed (over-tainting isn't the
    only structural-detection failure mode; under-counting via
    `CO_RETRIEVED` leakage is a real, observed second failure mode) —
    this is a scientific framing question, not an engineering task.
13. **Still open, the two real remaining blockers:** κ validation hasn't
    been run at all — the harness output now exists to draw the 100–150
    memory sample from, but the sample hasn't been drawn or hand-labeled.
    And the rubric can't be frozen (per this file's own §6/step-3 plan)
    until items 12(a)/12(b) above are resolved.
14. Once the rubric is frozen and κ validation passes, re-commit with a
    note marking it as the actual pre-registration timestamp; no data
    generation before that commit.

**Status: BLOCKED.** Blocker A (production `eval/` harness) — **closed**,
v1 scoped to labeling validation exists and ran successfully. Blocker B
(labeling protocol worked examples) — **substantially closed**, 8/10
filled from real data, 2 explicitly and honestly not found (a finding,
not a gap). Blocker C (κ validation) — **still fully open**, not started.
Two new scientific-framing items (12a/12b above) also block freezing the
rubric, independent of κ. Everything else in this document can continue
in parallel, but per the original plan: none of it clears the gate on
its own.
