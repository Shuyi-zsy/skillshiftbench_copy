"""Unit tests for MPCR first-tier component ablations.

Each test isolates one named component switch (Mask / Prior / Rerank) and checks
that an ablated run differs from full MPCR by exactly that mechanism.

Run: pytest src/MPCR/test_ablation.py
"""

import pytest

# MPCR's selection stage pulls in the browser-side numeric stack. The core
# install deliberately omits it, so this file is skipped there and exercised by
# the `[run]` job.
pytest.importorskip("numpy", reason="install skillshift-bench[run] to exercise MPCR")
pytest.importorskip("PIL", reason="install skillshift-bench[run] to exercise MPCR")

from skillshift.agents.mpcr import select_action as sa  # noqa: E402
from skillshift.agents.mpcr.select_action import (  # noqa: E402
    AblationConfig,
    CandidateFeatures,
)

# -----------------------------
# Config loading
# -----------------------------

_ABLATION_ENV = [
    "MPCR_MODE",
    "MPCR_DISABLE_MASK",
    "MPCR_DISABLE_PRIOR",
    "MPCR_DISABLE_RERANK",
    "MPCR_RANDOM_RERANK",
    "MPCR_RANDOM_SEED",
    "MPCR_SHORTLIST_K",
    "MPCR_RERANK_SCREENSHOT_DETAIL",
    "MPCR_DEBUG_PROMPT",
]


def _clear_ablation_env(monkeypatch):
    for name in _ABLATION_ENV:
        monkeypatch.delenv(name, raising=False)


def test_load_ablation_config_defaults_off(monkeypatch):
    # Arrange
    _clear_ablation_env(monkeypatch)

    # Act
    cfg = sa.load_ablation_config()

    # Assert
    assert cfg == AblationConfig(False, False, False)


def test_load_ablation_config_reads_truthy_env(monkeypatch):
    # Arrange
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("MPCR_DISABLE_MASK", "1")
    monkeypatch.setenv("MPCR_DISABLE_PRIOR", "true")
    monkeypatch.setenv("MPCR_DISABLE_RERANK", "On")

    # Act
    cfg = sa.load_ablation_config()

    # Assert
    assert cfg == AblationConfig(disable_mask=True, disable_prior=True, disable_rerank=True)


def test_load_ablation_config_ignores_falsey_env(monkeypatch):
    # Arrange
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("MPCR_DISABLE_MASK", "0")
    monkeypatch.setenv("MPCR_DISABLE_PRIOR", "false")
    monkeypatch.setenv("MPCR_DISABLE_RERANK", "")

    # Act
    cfg = sa.load_ablation_config()

    # Assert
    assert cfg == AblationConfig(False, False, False)


# -----------------------------
# Helpers / fixtures
# -----------------------------

def _candidate(idx: int, action: str, heuristic_score: float, task_relevance: float = 0.5) -> dict:
    return {
        "idx": idx,
        "action": action,
        "reason": "",
        "parsed": {"kind": "element", "name": "click"},
        "live": {},
        "obs_meta": {},
        "prereq": {"status": "unknown", "why": ""},
        "features": CandidateFeatures(task_relevance=task_relevance),
        "heuristic_score": heuristic_score,
    }


class _NoLLMAgent:
    """Agent exposing no LLM handle, so _find_llm returns None."""


# -----------------------------
# Mask ablation
# -----------------------------

def test_blank_live_has_no_executability_evidence():
    # Act
    live = sa._blank_live({"kind": "element"})

    # Assert
    assert live["exists"] is None
    assert live["visible"] is None
    assert live["enabled"] is None
    assert live["probe_error"] == "mask_disabled"


def test_disable_mask_keeps_readiness_neutral_for_element():
    # Arrange: with no feasibility evidence, an element prereq must be "unknown"
    live = sa._blank_live({"kind": "element"})
    obs_meta = sa._blank_obs_meta()

    # Act
    prereq = sa._infer_prerequisites({"kind": "element"}, live, obs_meta, current_obs={})

    # Assert
    assert prereq["status"] == "unknown"


# -----------------------------
# Prior ablation (shortlist ordering)
# -----------------------------

def test_prior_enabled_reorders_by_heuristic_score():
    # Arrange: generation order is worst-first; prior should pick the high score.
    enriched = [
        _candidate(0, "click(0)", heuristic_score=0.10),
        _candidate(1, "click(1)", heuristic_score=0.90),
    ]
    cfg = AblationConfig(disable_prior=False, disable_rerank=True)

    # Act: rerank disabled -> winner is the shortlist head
    winner, used_model, _trace, _stats = sa._rank_candidates(
        _NoLLMAgent(), sa.ActionRegistry(), {}, enriched, cfg
    )

    # Assert: prior reorders so the high-score candidate (idx 1) wins
    assert used_model is False
    assert winner["idx"] == 1


def test_disable_prior_keeps_generation_order():
    # Arrange: same candidates, but prior disabled -> keep generation order.
    enriched = [
        _candidate(0, "click(0)", heuristic_score=0.10),
        _candidate(1, "click(1)", heuristic_score=0.90),
    ]
    cfg = AblationConfig(disable_prior=True, disable_rerank=True)

    # Act
    winner, used_model, _trace, _stats = sa._rank_candidates(
        _NoLLMAgent(), sa.ActionRegistry(), {}, enriched, cfg
    )

    # Assert: generation-order head (idx 0) wins despite its lower score
    assert used_model is False
    assert winner["idx"] == 0


# -----------------------------
# Rerank ablation
# -----------------------------

def test_disable_rerank_takes_shortlist_head_without_llm():
    # Arrange: an agent WITH an llm handle would normally trigger pairwise compare.
    enriched = [
        _candidate(0, "click(0)", heuristic_score=0.90),
        _candidate(1, "click(1)", heuristic_score=0.10),
    ]
    cfg = AblationConfig(disable_rerank=True)

    called = {"compare": 0}

    def _fail_compare(*_args, **_kwargs):
        called["compare"] += 1
        raise AssertionError("LLM pairwise compare must not run when rerank is disabled")

    # Patch out the LLM path entirely.
    original_find = sa._find_llm
    original_cmp = sa._llm_compare_pair
    sa._find_llm = lambda _agent: {"type": "stub"}
    sa._llm_compare_pair = _fail_compare
    try:
        # Act
        winner, used_model, trace, _stats = sa._rank_candidates(
            _NoLLMAgent(), sa.ActionRegistry(), {}, enriched, cfg
        )
    finally:
        sa._find_llm = original_find
        sa._llm_compare_pair = original_cmp

    # Assert
    assert called["compare"] == 0
    assert used_model is False
    assert winner["idx"] == 0
    assert trace[0]["mode"] == "rerank_disabled"


# -----------------------------
# Named component-ablation variants (MPCR_MODE presets)
# -----------------------------

def test_mode_presets_map_to_expected_switches():
    # Arrange / Act / Assert: each named variant differs from full by its named mechanism.
    presets = sa.MODE_PRESETS
    assert presets["propose_only"] == AblationConfig(
        disable_mask=True, disable_prior=True, disable_rerank=True
    )
    assert presets["score_only"] == AblationConfig(
        disable_mask=True, disable_prior=False, disable_rerank=True
    )
    assert presets["rerank_only"] == AblationConfig(
        disable_mask=True, disable_prior=True, disable_rerank=False
    )
    assert presets["verify_only"] == AblationConfig(
        disable_mask=False, disable_prior=False, disable_rerank=True
    )
    assert presets["full"] == AblationConfig(
        disable_mask=False, disable_prior=False, disable_rerank=False
    )
    assert presets["random_rerank"] == AblationConfig(
        disable_mask=False, disable_prior=False, disable_rerank=False, random_rerank=True
    )


def test_mpcr_mode_env_selects_preset(monkeypatch):
    # Arrange
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("MPCR_MODE", "verify_only")

    # Act
    cfg = sa.load_ablation_config()

    # Assert
    assert cfg == AblationConfig(disable_mask=False, disable_prior=False, disable_rerank=True)


def test_mpcr_mode_accepts_aliases_and_annotations(monkeypatch):
    # Arrange: hyphenated + parenthetical annotation should normalize to verify_only.
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("MPCR_MODE", "Verify-Only (no rerank)")

    # Act
    cfg = sa.load_ablation_config()

    # Assert
    assert cfg == sa.MODE_PRESETS["verify_only"]


def test_mpcr_mode_takes_precedence_over_individual_switches(monkeypatch):
    # Arrange: a full-pipeline mode must win even if a stray disable switch is set.
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("MPCR_MODE", "full")
    monkeypatch.setenv("MPCR_DISABLE_MASK", "1")

    # Act
    cfg = sa.load_ablation_config()

    # Assert
    assert cfg == AblationConfig(False, False, False)


def test_mpcr_mode_applies_random_seed(monkeypatch):
    # Arrange
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("MPCR_MODE", "random_rerank")
    monkeypatch.setenv("MPCR_RANDOM_SEED", "7")

    # Act
    cfg = sa.load_ablation_config()

    # Assert
    assert cfg.random_rerank is True
    assert cfg.random_seed == 7


def test_unknown_mpcr_mode_raises(monkeypatch):
    # Arrange
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("MPCR_MODE", "bogus")

    # Act / Assert
    import pytest

    with pytest.raises(ValueError):
        sa.load_ablation_config()


def test_invalid_random_seed_raises(monkeypatch):
    # Arrange
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("MPCR_RANDOM_SEED", "not-an-int")

    # Act / Assert
    import pytest

    with pytest.raises(ValueError):
        sa.load_ablation_config()


# -----------------------------
# describe_mode labels
# -----------------------------

def test_describe_mode_labels_each_variant():
    assert sa.describe_mode(sa.MODE_PRESETS["propose_only"]) == "propose_only"
    assert sa.describe_mode(sa.MODE_PRESETS["score_only"]) == "score_only"
    assert sa.describe_mode(sa.MODE_PRESETS["rerank_only"]) == "rerank_only"
    assert sa.describe_mode(sa.MODE_PRESETS["verify_only"]) == "verify_only"
    assert sa.describe_mode(sa.MODE_PRESETS["full"]) == "full"
    assert sa.describe_mode(sa.MODE_PRESETS["random_rerank"]) == "random_rerank"


def test_describe_mode_reports_custom_for_unnamed_combo():
    # Mask disabled + prior on + rerank on is not one of the six named variants.
    cfg = AblationConfig(disable_mask=True, disable_prior=False, disable_rerank=False)
    assert sa.describe_mode(cfg) == "custom"


def test_rerank_only_alias_resolves(monkeypatch):
    # Arrange
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("MPCR_MODE", "reranking-only")

    # Act
    cfg = sa.load_ablation_config()

    # Assert
    assert cfg == sa.MODE_PRESETS["rerank_only"]


# -----------------------------
# Random-rerank control
# -----------------------------

def test_random_compare_pair_is_reproducible():
    # Arrange
    a = _candidate(0, "click(0)", heuristic_score=0.10)
    b = _candidate(1, "click(1)", heuristic_score=0.90)
    cfg = AblationConfig(random_rerank=True, random_seed=42)

    # Act
    first = sa._random_compare_pair(a, b, cfg)
    second = sa._random_compare_pair(a, b, cfg)

    # Assert: same seed + same pair -> identical decision, tagged as random_rerank.
    assert first == second
    assert first[0] in {"a", "b"}
    assert first[2] == "random_rerank"


def test_random_rerank_ignores_prior_score():
    # Arrange: idx 1 always has the higher score; a fair random judge must still
    # pick the lower-score candidate for at least some seeds.
    a = _candidate(0, "click(0)", heuristic_score=0.10)
    b = _candidate(1, "click(1)", heuristic_score=0.90)

    # Act: sweep seeds and collect which side wins.
    sides = {
        sa._random_compare_pair(a, b, AblationConfig(random_rerank=True, random_seed=s))[0]
        for s in range(50)
    }

    # Assert: both sides occur, so the choice is not driven by the prior score.
    assert sides == {"a", "b"}


def test_random_rerank_path_selects_from_shortlist_without_llm():
    # Arrange: rerank enabled via random control; no LLM handle is needed.
    enriched = [
        _candidate(0, "click(0)", heuristic_score=0.90),
        _candidate(1, "click(1)", heuristic_score=0.10),
    ]
    cfg = AblationConfig(random_rerank=True, random_seed=3)

    def _fail_compare(*_args, **_kwargs):
        raise AssertionError("LLM pairwise compare must not run for random rerank")

    original_find = sa._find_llm
    original_cmp = sa._llm_compare_pair
    sa._find_llm = lambda _agent: {"type": "stub"}
    sa._llm_compare_pair = _fail_compare
    try:
        # Act
        winner, used_model, trace, stats = sa._rank_candidates(
            _NoLLMAgent(), sa.ActionRegistry(), {}, enriched, cfg
        )
    finally:
        sa._find_llm = original_find
        sa._llm_compare_pair = original_cmp

    # Assert
    assert used_model is False
    assert winner["idx"] in {0, 1}
    assert any(entry["mode"] == "random_rerank" for entry in trace)
    assert stats.total_pairs == 0  # random control consults no LLM


def test_rerank_only_reranks_raw_candidates_via_llm(monkeypatch):
    # Arrange: three candidates where the score-top-2 differs from the
    # generation-order-first-2. Pin the shortlist to 2 so we can prove
    # rerank_only shortlists by generation order (ignoring the prior score).
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("MPCR_SHORTLIST_K", "2")
    enriched = [
        _candidate(0, "click(0)", heuristic_score=0.10),  # generation-order head
        _candidate(1, "click(1)", heuristic_score=0.20),
        _candidate(2, "click(2)", heuristic_score=0.90),  # would top a score sort
    ]
    cfg = AblationConfig(disable_mask=True, disable_prior=True, disable_rerank=False)

    compared = {"pairs": []}

    def _stub_compare(_agent, _handle, _registry, _obs, a, b, _ablation):
        compared["pairs"].append({a["idx"], b["idx"]})
        return "a", "stub", "llm_success"

    original_find = sa._find_llm
    original_cmp = sa._llm_compare_pair
    sa._find_llm = lambda _agent: {"type": "stub"}
    sa._llm_compare_pair = _stub_compare
    try:
        # Act
        winner, used_model, _trace, stats = sa._rank_candidates(
            _NoLLMAgent(), sa.ActionRegistry(), {}, enriched, cfg
        )
    finally:
        sa._find_llm = original_find
        sa._llm_compare_pair = original_cmp

    # Assert: the LLM ran (used_model) over the generation-order first two
    # candidates (idx 0 and 1), NOT the score-top candidate (idx 2).
    assert used_model is True
    assert stats.total_pairs == 1  # same LLM call count as the full pipeline
    assert compared["pairs"] == [{0, 1}]
    assert winner["idx"] == 0  # stub always prefers side "a"


def test_random_rerank_rank_candidates_is_reproducible():
    # Arrange
    enriched = [
        _candidate(0, "click(0)", heuristic_score=0.90),
        _candidate(1, "click(1)", heuristic_score=0.10),
    ]
    cfg = AblationConfig(random_rerank=True, random_seed=11)

    # Act
    w1, _, _, _ = sa._rank_candidates(_NoLLMAgent(), sa.ActionRegistry(), {}, list(enriched), cfg)
    w2, _, _, _ = sa._rank_candidates(_NoLLMAgent(), sa.ActionRegistry(), {}, list(enriched), cfg)

    # Assert
    assert w1["idx"] == w2["idx"]
