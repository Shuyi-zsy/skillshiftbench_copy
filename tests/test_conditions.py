"""Condition <-> environment mapping is the single place the six paper columns
are defined.  Every other module must go through it."""


from dataclasses import FrozenInstanceError

import pytest

from skillshift import conditions
from skillshift.errors import UnknownConditionError


def test_exposes_exactly_the_six_paper_conditions_in_table_order():
    assert conditions.CONDITIONS == (
        "src",
        "src-perc",
        "src-exec",
        "tgt",
        "tgt-perc",
        "tgt-exec",
    )


@pytest.mark.parametrize(
    "name,site_version,perceptual,execution",
    [
        ("src", "v1", False, False),
        ("src-perc", "v1", True, False),
        ("src-exec", "v1", False, True),
        ("tgt", "v2", False, False),
        ("tgt-perc", "v2", True, False),
        ("tgt-exec", "v2", False, True),
    ],
)
def test_resolves_each_condition_to_its_flags(name, site_version, perceptual, execution):
    # Arrange / Act
    spec = conditions.resolve(name)

    # Assert
    assert spec.name == name
    assert spec.site_version == site_version
    assert spec.perceptual_shift is perceptual
    assert spec.execution_shift is execution


def test_resolve_is_case_insensitive_and_accepts_underscores():
    assert conditions.resolve("TGT_EXEC") == conditions.resolve("tgt-exec")


def test_resolve_raises_with_the_valid_names_listed():
    with pytest.raises(UnknownConditionError) as excinfo:
        conditions.resolve("target-exec")
    assert "tgt-exec" in str(excinfo.value)


def test_from_flags_is_the_exact_inverse_of_resolve():
    for name in conditions.CONDITIONS:
        spec = conditions.resolve(name)
        assert (
            conditions.from_flags(
                site_version=spec.site_version,
                perceptual_shift=spec.perceptual_shift,
                execution_shift=spec.execution_shift,
            )
            == spec
        )


def test_from_flags_rejects_combining_both_shifts():
    # The paper defines no cell with both shifts active; silently accepting one
    # would produce a result that has no column to go in.
    with pytest.raises(UnknownConditionError):
        conditions.from_flags(site_version="v1", perceptual_shift=True, execution_shift=True)


def test_from_flags_rejects_an_unknown_site_version():
    with pytest.raises(UnknownConditionError):
        conditions.from_flags(site_version="v3", perceptual_shift=False, execution_shift=False)


def test_to_env_sets_both_upper_and_lower_case_names():
    # The harness reads WEBSITE first and falls back to `website`; emitting only
    # one of the two lets a stale variable in the user's shell win silently.
    env = conditions.to_env(site="magento", condition="tgt-exec")

    assert env["website"] == "admin"
    assert env["WEBSITE"] == "admin"
    assert env["site_version"] == env["SITE_VERSION"] == "v2"
    assert env["with_perceptual_shift"] == env["WITH_PERCEPTUAL_SHIFT"] == "false"
    assert env["with_execution_shift"] == env["WITH_EXECUTION_SHIFT"] == "true"


def test_to_env_uses_the_harness_site_key_not_the_paper_name():
    assert conditions.to_env(site="magento", condition="src")["website"] == "admin"
    assert conditions.to_env(site="gitlab", condition="src")["website"] == "gitlab"
    assert conditions.to_env(site="wordpress", condition="src")["website"] == "wordpress"


def test_condition_spec_is_immutable():
    spec = conditions.resolve("src")
    with pytest.raises(FrozenInstanceError):
        spec.site_version = "v2"
