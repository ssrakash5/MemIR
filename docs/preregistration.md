# Pre-registration

**Status: skeleton draft, NOT the committed pre-registration.** Per
week1_execution_plan.md §4, this file must be "committed and timestamped
before any data is generated" — but committing it as final before
`docs/positioning.md` and `docs/labeling_protocol.md` are validated (both
still marked draft/TODO as of this writing) would pre-register hypotheses
built on an unread literature review and an unvalidated labeler. Treat this
as the structure to fill in, not the timestamp that gates data generation.
**Do not generate experiment data against this version.**

---

## 1. Hypotheses

- **H1:** Precision degrades monotonically with derivation depth.
- **H2:** Precision degrades with increasing `top_k`.
- **H3:** A non-trivial fraction of `CARRIES` descendants are laundered (no
  surviving marker tokens).

## 2. Variables

See `configs/experiment_grid.yaml` (§2 of the plan) for the full factorial:

- Independent: `top_k` ∈ {1,3,5,10}; depth ∈ {0..5}; similarity threshold ∈
  {none, 0.5, 0.7, 0.85}; injection style ∈ {direct instruction, embedded
  fact, authoritative framing, multi-hop setup}; summarization prompt ∈
  {terse, verbose, structured}.
- Dependent: precision @ depth d, recall under thresholding, blast radius,
  laundering rate.
- Controls: model, seed, corpus size, embedding model — **not yet pinned to
  specific version strings**, see `TBD` markers in
  `configs/experiment_grid.yaml`.

**Open issue carried over from experiment_grid.yaml:** the full factorial is
13,824 cells, which is very likely infeasible to run as pre-registered.
Section 4 below cannot be finalized until a marginalization decision is made
and written down explicitly — see the note left in
`configs/experiment_grid.yaml`.

## 3. Labeling protocol

See `docs/labeling_protocol.md` (§3 of the plan). **Not yet validated**: the
κ Cohen's-kappa check against 100–150 hand-labeled memories has not been
run, and the automated-signal combination rule is still undecided. §4 of the
plan is explicit that this protocol reference is part of what gets
pre-registered — it should not be treated as locked until that validation
step passes (κ ≥ 0.6).

## 4. Sample sizes

**Not yet determined.** Depends on:
- Resolving the 13,824-cell factorial down to a feasible pre-registered
  design (see §2 above).
- ≥3 seeds per condition per `CLAUDE.md` standards — already reflected as a
  control in `configs/experiment_grid.yaml`.
- Target scale from `docs/labeling_protocol.md`: ≥200 injection instances
  across ≥4 styles, chains to depth ≥3, as a floor for the labeling
  validation corpus — not necessarily the same N as the full experimental
  run.

## 5. Statistics

- Paired bootstrap, 10,000 resamples, for all point estimates.
- 95% confidence intervals on every reported number.
- Wilcoxon signed-rank test for paired comparisons (e.g., precision at
  depth d vs. d+1 within the same seed/condition).
- This matches `CLAUDE.md`'s standing standard (mean ± 95% CI, bootstrap
  10k resamples) — no deviation needed here.

## 6. Falsification conditions

Stated in advance, to be reported regardless of outcome:

- **If precision remains >0.8 at depth 4**, provenance-based containment is
  practical as-is and this paper's premise is wrong.
- **If laundering rate is <5%**, the phenomenon motivating the work is rare.

Pre-registering these conditions is what makes a negative result
publishable rather than embarrassing — per the plan, both outcomes must be
reported honestly if observed, not quietly reframed after the fact.

---

## Before this can be committed as the real pre-registration

1. `docs/positioning.md` needs your full read of MemLineage/MemAudit behind
   it, not the current second-hand draft.
2. `docs/labeling_protocol.md` needs the κ validation run and passed, and
   the 10 worked examples filled in from real `spike/05_e2e.py` output.
3. The experiment grid's 13,824-cell factorial needs an explicit
   marginalization decision, recorded in §4 above, not left as "full grid"
   fiction.
4. Once 1–3 are done, this file should be re-committed with a note in the
   commit message marking it as the actual pre-registration timestamp, and
   no data generation should happen before that commit per `CLAUDE.md`.
