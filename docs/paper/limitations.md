<!-- DRAFT — Markdown first. Written now, per week5.md's own advice, while
the reasons for each cut/scope decision are still fresh, not
reconstructed from memory during the Week 6 draft push. -->

# Limitations

**Exposure is not causation.** Our blast-radius metrics measure
whether a memory is reachable from a compromised root under a given
provenance policy and whether it actually carries the harmful semantic
content — they do not establish that the exposure caused any real-world
harm (an action taken, a decision made). A memory can be correctly
flagged as exposed and contaminated without ever being acted upon.

**Synthetic, LLM-authored corpus; real-document validation is limited in
scale.** All 30 main-corpus scenarios are hand-authored specifications
with LLM-generated surface text, not derived from real production
agent-memory traces or naturally occurring attacks. We added a 20-document
public-source validation slice (§IV-G/Results) spanning five domains,
which reproduced the principal provenance/containment tradeoffs
(`depth_aware`'s ~30% inflation reduction, structural precision/recall)
but yielded a substantially higher and more heterogeneous surface-marker
laundering rate (19.1% [6.9%, 33.1%] scenario-level vs. 0.79% in the
synthetic corpus). The slice is intended as an ecological-validity check,
not an independently powered benchmark: documents were selected from
public sources, one controlled compromise was constructed per document,
and the resulting 20 scenarios do not represent production agent-memory
traffic at any scale or diversity approaching real deployment. The gap
between the synthetic and real-document laundering rates — and its wide
confidence interval, driven by real per-scenario heterogeneity rather than
measurement noise — cautions against treating synthetic-corpus effect
sizes as directly representative of deployment settings.

**Single embedding model, never pinned as the paper's actual choice.**
Retrieval and the H2 attribution-score analysis both use
`all-MiniLM-L6-v2` (sentence-transformers) throughout — explicitly
flagged in our own design documents as a placeholder pending a final
pinned choice, not yet revisited before this draft. We checked, rather
than merely asserted, that this does not change H2's qualitative
result: recomputing the thresholded policy with a second,
architecturally different embedding model (`all-mpnet-base-v2`,
Results) on a scoped subset (gpt-4o-mini, seed 0, all 24 poisoned
scenarios) reproduces the same precision-up/inflation-down trend as
the threshold tightens. The absolute threshold values and the
magnitude of recall erosion do differ between embedding spaces (recall
erodes far less under `all-mpnet-base-v2` than under
`all-MiniLM-L6-v2` at the strictest threshold tested), so the precise
precision/recall frontier reported for the main corpus is still
specific to `all-MiniLM-L6-v2` — only the qualitative existence and
direction of the frontier has been checked against a second embedding
model, not its exact shape.

**`attribution_threshold` was operationalized after the fact, not
specified in the original design.** The experimental grid named this
analysis factor without defining a continuous per-edge score to
threshold. We chose cosine similarity between parent/child memory
embeddings — an explicit, defensible, but not the only possible choice
(a trained classifier or NLI-entailment-based score would also have
been reasonable) — documented as a dated decision, not silently
assumed. The same applies to the `depth_aware` containment policy,
which the design named as "one baseline, one proposed method" without
specifying the proposed method's algorithm; we operationalized it as a
depth-windowed hybrid of conservative and structural-only propagation.
Both choices are reasoned and stated, but a different operationalization
of either could produce a different quantitative frontier. We
accordingly present `depth_aware` as a proof-of-concept operating
point demonstrating that depth-dependent provenance decisions occupy a
useful position on the quarantine/recall frontier — not as a proposed,
tuned, or universally optimal containment algorithm. We ran two
targeted robustness checks against exactly this concern rather than
leaving it as an unaddressed threat to validity: sweeping
`depth_aware_window` ∈ {1, 2, 3} (Results) shows the flagged-object/
missed-contamination tradeoff moves smoothly as the window expands
(6.00/0.278, 7.00/0.206, 8.00/0.141 objects flagged/missed
contamination, respectively, at depth 5) rather than window=2 being a
singular hand-picked point; and recomputing H2's thresholded policy
with a second, architecturally different embedding model
(all-mpnet-base-v2 in place of all-MiniLM-L6-v2, Results) checks
whether the precision/recall attribution frontier is an artifact of
one embedding space.

**Conservative propagation gives recall 1.0 largely by construction.**
The context-exposure/`flat_transitive` policy's near-perfect recall
(R_BR ≈ 1.0 across nearly all conditions) is expected given how it is
defined (flag anything reachable via any edge), not a discovery — the
paper's contribution is characterizing the precision *cost* of that
recall and the conditions under which cheaper (structural-only,
thresholded, depth-aware) policies still miss real contamination, not
the recall-1.0 fact itself.

**One containment-cost metric turned out uninformative in our
topology.** Our original operationalization of $C_{regen}$ (distinct
generating runs touched) does not differentiate `flat_transitive` from
`depth_aware` in this harness's design, because the always-continuing
structural lineage guarantees every depth is touched under either
policy. We report this honestly (Method, Results) and use flagged
*object count* as the metric that actually demonstrates the containment
tradeoff instead — but it means our depth-based cost metric, as
originally specified, does not do the job we designed it to do, and a
different harness topology (e.g. one where structural lineage can
itself terminate early) might make it more informative.

**Depth-continuation rule limits branching complexity.** Only the
compromised root's own lineage (`child_1`) continues across depths;
sibling writes are fresh at each depth rather than themselves branching
further. This keeps the corpus tractable and auditable but means we do
not study *nested* branching (a sibling write itself spawning further
descendants) — a real agent's memory graph could have branching at
every node, not just along one continuing spine.

**Three models, one derivation prompt template.** We test three LLMs
(gpt-4o-mini, gpt-4o, Llama-3.3-70B-Instruct) with an identical,
un-tuned prompt template, by design — this isolates the model as the
variable of interest, but it also means results may not reflect each
model's *best-achievable* derivation behavior under a prompt
specifically tuned for it, and does not cover reasoning-specialized or
much smaller/larger models.

**Platform-level content filtering caused incomplete coverage for one
model.** 30 of 21,600 planned traces (Llama-3.3-70B-Instruct only,
0.14% of that model's grid) could not be generated because Azure's
content-safety filter rejected the underlying request (flagged as
"Jailbreak") — a platform behavior, not a code or methodology defect,
but one that means Llama-3.3-70B's corpus has a small number of
missing cells the other two models' corpora do not, concentrated in
`authoritative_framing`-style scenarios and `write_fanout=3`
conditions. Left as genuine missing data, not imputed.

**Human validation now includes a human-human baseline.** Cohen's κ
between the automated labeler and one human's blind labels on a
120-sample calibration set is 0.87–0.88. A second independent human
annotator blind-labeled the same 120-sample set afterward, giving a
human-human baseline of κ = 0.9277 (115/120 raw agreement) — close to
the pipeline's own agreement with either human, and informative rather
than merely reassuring: all 5 human-human disagreements fall on the
same REFERENCES-vs-CARRIES compositional boundary already flagged
below as the labeler's weakest point, indicating that boundary reflects
genuine rubric ambiguity rather than a labeler-specific failure (see
Discussion).

**Marker-token extraction for H3 is mechanical, not human-authored.**
No scenario specification includes an explicit `marker_tokens` field;
we extract them via a regex-plus-entity-substring heuristic verified to
produce at least one marker per scenario, but not independently
reviewed the way the scenario corpus's structural ground truth was.
</content>
