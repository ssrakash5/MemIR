<!-- DRAFT — Markdown first. Synthesizes Results/Limitations into
operational implications; does not introduce new numbers or claims
beyond what H1-H4, the clean-control baseline, the human-human kappa
result, the real-document validation slice, and the H2/H4 robustness
checks (Results) already establish. -->

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

Two properties of this frontier are worth being confident about rather
than merely hoping generalize: whether it is an artifact of the one
embedding model used to threshold attribution, and whether
`depth_aware`'s reported operating point is a hand-picked good result
rather than a real point on a continuous tradeoff. We checked both
directly (Results) rather than leaving them as unaddressed threats to
validity. Re-thresholding H2 with a second, architecturally different
embedding model reproduces the same precision-up/inflation-down trend
as attribution strictness increases, even though the absolute
threshold values and the amount of recall erosion differ between
embedding spaces — the frontier's *existence* is not an artifact of
`all-MiniLM-L6-v2`, even though its precise shape is still reported
only for that model. Sweeping `depth_aware`'s conservative window
across {1, 2, 3} hops shows the flagged-object/missed-contamination
tradeoff move smoothly and monotonically, not jump discontinuously
around window=2 — `depth_aware` is one legible point on a family of
depth-dependent policies, not a single number chosen to look good.

## No model is uniformly safer — provenance metadata needs to know which model wrote what

The cross-model asymmetry that recurs across H1, H3, and H4 (gpt-4o-mini
shows the steepest inflation growth and the largest `depth_aware`
missed-contamination cost; Llama-3.3-70B shows by far the most
laundering under `paraphrase`) is not just a comparison result — it has
a direct operational consequence. A deployment that mixes models (a
cheap model for routine derivation, a stronger model for high-stakes
writes, or a fallback model during an outage) should not assume that
one propagation policy tuned against a single model's profile performs
equally well against another's — our results motivate recording which
model produced a given derived memory, not just the structural edges
between memories, and evaluating containment policy as a function of
that model identity, rather than assuming a uniform policy is safe by
default. A `depth_aware` window tuned against gpt-4o's
missed-contamination profile is not obviously the same policy for a
memory Llama-3.3-70B wrote, though we did not test whether a uniform
policy is in fact acceptable in any particular deployment — only that
the underlying per-model behavior is heterogeneous enough that the
question is worth asking. We did not evaluate policy parameters
conditioned on model identity; this paper establishes that the
asymmetry is real and large enough to matter, not what the
model-conditioned policy should be.

## The compositional boundary is real, not a labeler artifact

The REFERENCES-class weakness flagged in Limitations (precision 0.75,
recall 0.46, concentrated in `multi_hop_setup` scenarios) could, before
this session, have been explained two ways: genuine rubric ambiguity at
the CARRIES/REFERENCES boundary, or a labeler-specific failure. The
human-human $\kappa$ baseline computed after the original submission
draft ($\kappa = 0.9277$, 115/120 raw agreement) supports the former
interpretation: all five disagreements between two independent human
annotators fell on exactly that same boundary — two true statements
placed side by side versus a combined assertion of the full
compositional claim. Humans genuinely disagree here too, though two
annotators over 120 examples is evidence for, not a settled ontology of,
that boundary. A second, independent piece of evidence points the same
direction: the manual, full-population read of all 46 `child_2=CARRIES`
cases in the real-document slice (Results) found that 40/46 explicitly
contained the injected claim's marker or wording, meaning the automated
labeler's CARRIES calls are not simply pattern-matching noise on
held-out data either. Together, these suggest the operational
implication is not that the labeling pipeline needs more tuning at the
CARRIES/REFERENCES boundary specifically; it is that any deployment
using this framework (or any automated labeler at all) should treat
multi-hop/compositional exposure flags as lower-confidence by
construction and route them to human review specifically, rather than
trusting the same confidence threshold that works for single-premise
claims.

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
precision/recall/cost frontier to reason about, and, to our knowledge,
this paper is the first measurement of what that frontier looks like
under branching derivation.

## What this changes about where to look next

Before this session, the natural next step for the REFERENCES-class
weakness would have been "improve the labeler." The human-human
baseline redirects that: the next highest-value step is not
labeler tuning but a targeted human study of the compositional boundary
specifically — more `multi_hop_setup`-style scenarios, more annotators,
a rubric refinement aimed at that one boundary rather than the rubric
as a whole. Similarly, the cross-model asymmetry's practical weight
(Discussion, above) suggests that a natural next extension of the
real-document validation slice completed in this paper (Results,
Limitations) is to construct mixed-model traces specifically, not just
more naturalistic content, since the asymmetry we measure here on
synthetic scenarios — and confirm, directionally, on real documents —
is exactly the kind of effect that could look different — larger,
smaller, or differently distributed across models — on real production
derivation patterns where a single trace's writes are not all produced
by the same model.
