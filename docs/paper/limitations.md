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

**Synthetic, LLM-authored corpus.** All 30 scenarios are hand-authored
specifications with LLM-generated surface text, not derived from real
production agent-memory traces or naturally occurring attacks. We
deliberately designed a real-document validation slice into the
original study plan (10–20 real documents, for ecological validity)
specifically to partially address this; it was not completed within
this paper's timeline and is left as a genuine, acknowledged gap rather
than a claim we did not intend to make.

**Single embedding model, never pinned as the paper's actual choice.**
Retrieval and the H2 attribution-score analysis both use
`all-MiniLM-L6-v2` (sentence-transformers) throughout — explicitly
flagged in our own design documents as a placeholder pending a final
pinned choice, not yet revisited before this draft. Results involving
embedding similarity (H2's threshold sweep) should be read with this
caveat; a different embedding model could shift the precise
precision/recall frontier, though we would not expect it to change the
qualitative existence of a frontier.

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
tuned, or universally optimal containment algorithm.

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

**Human validation is single-annotator.** Cohen's κ was computed
against one human's blind labels on a 120-sample calibration set, not
a human-human inter-annotator baseline — a low κ could in principle
reflect genuine rubric ambiguity as easily as labeler failure, and we
cannot fully separate those explanations without a second human
annotator on the same sample.

**Marker-token extraction for H3 is mechanical, not human-authored.**
No scenario specification includes an explicit `marker_tokens` field;
we extract them via a regex-plus-entity-substring heuristic verified to
produce at least one marker per scenario, but not independently
reviewed the way the scenario corpus's structural ground truth was.
</content>
