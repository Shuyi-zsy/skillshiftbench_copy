"""MPCR: Masked Prior-guided Candidate Reranking.

Vendored from the paper's artifact.  The four-stage pipeline
(Propose -> Mask -> Prior -> Rerank) and all six ablation variants are
unchanged; the differences from the artifact are import paths, a lazy import of
the optional embedding stack, and skill-call reporting through
`skillshift.agents.events.SkillRecorder`.
"""
