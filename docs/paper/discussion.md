<!-- DRAFT — Markdown first. Synthesizes Results/Limitations into
operational implications; does not introduce new numbers or claims
beyond what H1-H4, the clean-control baseline, and the human-human
kappa result already establish. -->

# Discussion

## The frontier is the deliverable, not a defect

H1 and H2 together describe a real precision/recall frontier, and the
practical upshot for an operator is that there is no policy choice that
dominates on every axis. Conservative (context-exposure) propagation
is the right default when the cost of a missed exposure exceeds the
cost of an unnecessary quarantine — a compliance escalation, a legal
hold, an incident where under-flagging is the failure mode that ends
careers. Attribution thresholding is the right choice when quarantine
itself is expensive (every flagged object means a regenerated write, a
paused workflow, a human review) and some false-negative risk is
acceptable — but H2's finding that an aggressive threshold (0.85)
specifically prunes the weakly-attributed `CO_RETRIEVED` edges that are
sometimes the *only* path to real contamination means that choice
should be made deliberately, not as a default tuning knob turned up
for cleanliness. `depth_aware` (H4) is a third point on this frontier,
not a replacement for either: it recovers much of conservative
propagation's near-root recall while cutting long-tail over-quarantine
by roughly 30%, at a missed-contamination cost concentrated beyond
depth 2. None of these is "the" answer; which one an operator should
run depends on what a false positive costs them relative to a false
negative, a judgment this paper does not make on the operator's
behalf.

## No model is uniformly safer — provenance metadata needs to know which model wrote what

The cross-model asymmetry that recurs across H1, H3, and H4 (gpt-4o-mini
shows the steepest inflation growth and the largest `depth_aware`
missed-contamination cost; Llama-3.3-70B shows by far the most
laundering under `paraphrase`) is not just a comparison result — it has
a direct operational consequence. A deployment that mixes models (a
cheap model for routine derivation, a stronger model for high-stakes
writes, or a fallback model during an outage) cannot apply one
propagation policy uniformly across its whole memory graph and expect
uniform containment quality. Provenance metadata needs to record which
model produced a given derived memory, not just the structural edges
between memories, so that containment policy can be conditioned on it —
a `depth_aware` window tuned against gpt-4o's missed-contamination
profile is not the same policy for a memory Llama-3.3-70B wrote. We did
not evaluate policy parameters conditioned on model identity; this
paper establishes that the asymmetry is real and large enough to
matter, not what the model-conditioned policy should be.

## The compositional boundary is real, not a labeler artifact

The REFERENCES-class weakness flagged in Limitations (precision 0.75,
recall 0.46, concentrated in `multi_hop_setup` scenarios) could, before
this session, have been explained two ways: genuine rubric ambiguity at
the CARRIES/REFERENCES boundary, or a labeler-specific failure. The
human-human $\kappa$ baseline computed after the original submission
draft ($\kappa = 0.9277$, 115/120 raw agreement) settles this: all five
disagreements between two independent human annotators fell on exactly
that same boundary — two true statements placed side by side versus a
combined assertion of the full compositional claim. Humans genuinely
disagree here too. The operational implication is not that the
labeling pipeline needs more tuning at this boundary; it is that any
deployment using this framework (or any automated labeler at all)
should treat multi-hop/compositional exposure flags as lower-confidence
by construction and route them to human review specifically, rather
than trusting the same confidence threshold that works for
single-premise claims.

## Where this sits relative to prevention and reactive investigation

Related Work positions this paper against MemLineage (preventive
gating) and MemAudit (reactive, triggered by an observed harmful
event) as answering a different question, not a better one. Read
together with those two, the three form a plausible pipeline rather
than three competing solutions to the same problem: preventive lineage
enforcement is the first line of defense and, when its attribution
threshold holds, may prevent a compromised label from ever reaching a
sensitive action; reactive investigation triggers once a harmful
outcome is actually observed and needs to identify which memory caused
*that specific* failure; post-incident reconstruction — this paper's
object — is what an operator needs the moment either of those signals
fires but before its full downstream consequence is known: a
preventive gate that is bypassed, delayed, or simply not deployed on
every write path still leaves the question "given that this one memory
is compromised, what else is," which is the question this paper
answers. None of the three papers this compares against evaluates that
question over a branching graph with a measured
precision/recall/inflation frontier, which is the gap this work fills,
not a claim that provenance tracking or persistent-memory-poisoning
awareness themselves are novel.

## When this framework is, and is not, the right tool

The metrics and policies here assume an agent architecture where
derivation provenance (which memories were retrieved into which write)
can be logged at generation time — true of retrieval-augmented agents
built on an explicit vector store or structured memory log, the
architecture this paper's threat model assumes. An agent whose memory
is an opaque fine-tuned weight update, or whose retrieval/write path is
not instrumented, cannot use this framework at all; blast-radius
reconstruction is a capability that has to be designed in before an
incident, not retrofitted after one. This is worth stating plainly
because it bounds the claim: we are not arguing every agent memory
system should adopt these specific metrics, only that systems capable
of logging provenance in the first place have a measurable
precision/recall/cost frontier to reason about, and this paper is the
first measurement of what that frontier looks like under branching
derivation.

## What this changes about where to look next

Before this session, the natural next step for the REFERENCES-class
weakness would have been "improve the labeler." The human-human
baseline redirects that: the next highest-value step is not
labeler tuning but a targeted human study of the compositional boundary
specifically — more `multi_hop_setup`-style scenarios, more annotators,
a rubric refinement aimed at that one boundary rather than the rubric
as a whole. Similarly, the cross-model asymmetry's practical weight
(Discussion, above) suggests the real-document validation slice already
planned as future work (Limitations) should prioritize mixed-model
traces specifically, not just naturalistic content, since the
asymmetry we measure here on synthetic scenarios is exactly the kind of
effect that could look different — larger, smaller, or differently
distributed across models — on real production derivation patterns.
