# Pre-registration

**Status: skeleton draft, NOT the committed pre-registration.** Updated
2026-08-11 to reflect the repositioned research question in
`docs/positioning.md` (post-incident blast-radius reconstruction in
branching memory graphs, not the original precision-of-exposure-flagging
framing, which failed the Tuesday gate — see `docs/positioning.md` for the
full correction). Still not ready to be the timestamp that gates data
generation: `docs/labeling_protocol.md`'s κ validation hasn't run, and
`configs/experiment_grid.yaml` hasn't been updated to match the new
dependent variables yet. **Do not generate experiment data against this
version.**

---

## 1. Hypotheses (revised 2026-08-11 — supersedes the original H1–H3)

- **H1 — Blast-radius inflation.** Conservative provenance has high
  blast-radius recall but suffers superlinear blast-radius inflation
  (E_flagged / E_true) as retrieval fan-out and write fan-out grow.
- **H2 — Precision/recall frontier shifts with depth.** Attribution
  thresholds reduce over-tainting (lower inflation) but introduce
  false-negative exposure paths (lower recall), and this precision/recall
  frontier shifts with derivation depth.
- **H3 — Execution provenance outlasts surface traceability.** Surface-level
  (lexical/marker-token) traceability degrades faster with transformation
  strength (paraphrase/summarize/refine) than execution-provenance
  traceability does. This is a direct comparison of content-based vs.
  execution-provenance traceability — not a claim that any prior system
  "misses" laundering (see `docs/positioning.md`'s correction on this
  point).
- **H4 — Depth-aware containment reduces over-quarantine.** Thresholding or
  pruning by attribution confidence substantially reduces unnecessary
  quarantine relative to flat transitive taint, while preserving high
  action-level containment recall.

## 2. Variables

See `configs/experiment_grid.yaml` for the current factorial — **not yet
updated for the repositioned dependent variables below; this is the next
concrete task.**

- Independent (currently in the grid, subject to revision): `top_k`,
  derivation depth, similarity/attribution threshold, injection style,
  summarization/transformation prompt (terse/verbose/structured — should
  probably be extended or reframed as paraphrase/summarize/refine to match
  MemLineage's own transformation vocabulary in §5.3, for comparability).
- Dependent (revised — replaces precision-at-depth/laundering-rate as
  primary outcomes): blast-radius precision (E_correct/E_flagged),
  blast-radius recall (E_correct/E_true), inflation ratio
  (E_flagged/E_true), containment cost (what quarantine/regeneration
  actually costs under a given policy), and the H3 comparison metric
  (surface-marker survival vs. execution-provenance recall across
  transformation strength).
- New independent variable needed: **branching factor** — writes-per-run
  and retrievals-per-run, since the repositioned question is specifically
  about branching graphs, not the mostly-chain-shaped evaluation MemLineage
  used. `configs/experiment_grid.yaml` currently has no branching-factor
  axis at all — this is a gap, not just a relabeling.
- Controls: model, seed, corpus size, embedding model — still `TBD`.

**Open issue carried over from experiment_grid.yaml:** the full factorial
(as currently specified, pre-repositioning) is 13,824 cells. Adding a
branching-factor axis makes this worse, not better — the marginalization
decision is now more urgent, not resolved by the repositioning.

## 3. Labeling protocol

See `docs/labeling_protocol.md`. **Not yet validated**: κ check against
100–150 hand-labeled memories not run; automated-signal combination rule
undecided. Additionally, the labeling protocol was written for the original
CARRIES/REFERENCES/CLEAN framing (content-level labels) — worth checking
whether blast-radius reconstruction needs a parallel *structural* ground
truth (was object X actually causally downstream of compromised root R?)
separate from the content-level three-way label. These may turn out to be
different, complementary ground-truth axes: one about what a memory
*asserts*, one about what it's *derived from*. Needs a decision before this
section can be finalized.

## 4. Sample sizes

**Not yet determined.** Same blockers as before (grid marginalization) plus
the new branching-factor axis increasing the space further.

## 5. Statistics

- Paired bootstrap, 10,000 resamples, for all point estimates.
- 95% confidence intervals on every reported number.
- Wilcoxon signed-rank test for paired comparisons.
- Unchanged from the original draft — `CLAUDE.md`'s standing standard
  applies regardless of the repositioning.

## 6. Falsification conditions (revised to match H1–H4)

Stated in advance, to be reported regardless of outcome:

- **If blast-radius inflation stays near 1.0x (i.e., conservative
  provenance is already close to precise) across the tested fan-out
  range**, the over-tainting problem motivating this paper doesn't
  materialize in practice and the premise is wrong.
- **If depth-aware containment (H4) doesn't measurably reduce over-
  quarantine relative to flat transitive taint**, the paper's proposed
  remedy has no advantage over the naive baseline.
- **If execution-provenance recall degrades at the same rate as surface
  traceability (H3 null)**, the case for provenance over simpler
  content-matching approaches weakens substantially.

## Before this can be committed as the real pre-registration

1. ~~`docs/positioning.md` needs your full read of MemLineage/MemAudit~~ —
   done 2026-08-11, and it changed the research question. This document has
   been updated to match, but variables/grid have not been fully reconciled
   yet (see §2 above).
2. `docs/labeling_protocol.md` needs the κ validation run and passed, the
   10 worked examples filled in (1/10 done), and a decision on whether a
   separate structural ground-truth axis is needed (§3 above).
3. `configs/experiment_grid.yaml` needs: (a) the marginalization decision
   for the (now larger) factorial, (b) a branching-factor axis added, (c)
   dependent variables updated from precision-at-depth/laundering-rate to
   blast-radius precision/recall/inflation/containment-cost.
4. Once 1–3 are done, re-commit with a note marking it as the actual
   pre-registration timestamp; no data generation before that commit.
