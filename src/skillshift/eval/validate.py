"""The five leaderboard checks.

`skillshift validate` and the leaderboard CI run exactly this code, so a
submitter finds out locally whether a pull request will be rejected.

    1. schema         the file matches results.schema.json (and receipt.schema.json)
    2. coverage       all ten slots per metric are present; every null has a reason
    3. marginals      task counts are the official ones, and
                      mean(3 websites) == mean(6 conditions) == overall
    4. metric-ranges  values are in range, and SFR carries a low-confidence flag
                      whenever it rests on too few skill invocations
    5. receipt        a self-reported entry ships a receipt whose provenance is
                      official and whose embedded aggregate matches the submission

Check 3 is the one that does the work now that per-task results are not
published.  Because both marginals are macro-averages of the same eighteen
cells, they must agree with each other and with the overall value; a single
mistyped number breaks the identity.  Note that this is a *macro* average --
websites are not weighted by task count.  See `skillshift.eval.metrics`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .. import __version__
from ..conditions import CONDITIONS
from ..sites import SITE_NAMES, TOTAL_TASKS, task_counts
from . import metrics as metrics_mod
from . import schema as schema_mod

CHECKS: tuple[str, ...] = ("schema", "coverage", "marginals", "metric-ranges", "receipt")

DEFAULT_SUPPORTED_HARNESS_VERSIONS: tuple[str, ...] = (__version__, "n/a")

#: Labels the leaderboard renders next to an entry.
LOW_CONFIDENCE_LABEL = "low-confidence"


@dataclass(frozen=True)
class Finding:
    """One problem found by one check."""

    check: str
    severity: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.check}: {self.message}"


@dataclass(frozen=True)
class ValidationReport:
    """The outcome of validating one submission."""

    findings: tuple[Finding, ...] = ()
    labels: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == "error")

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        verdict = "PASS" if self.ok else "FAIL"
        return (
            f"{verdict}: {len(self.errors)} error(s), {len(self.warnings)} warning(s)"
            + (f", labels: {dict(self.labels)}" if self.labels else "")
        )


def _error(check: str, message: str) -> Finding:
    return Finding(check=check, severity="error", message=message)


def _warning(check: str, message: str) -> Finding:
    return Finding(check=check, severity="warning", message=message)


def validate_submission(
    results: Mapping[str, Any],
    receipt: Mapping[str, Any] | None = None,
    *,
    official_digests: Mapping[str, str] | None = None,
    supported_harness_versions: Sequence[str] | None = None,
) -> ValidationReport:
    """Run all five checks and return every finding."""
    supported = tuple(supported_harness_versions or DEFAULT_SUPPORTED_HARNESS_VERSIONS)

    findings: list[Finding] = []
    findings.extend(_check_schema(results, receipt))

    # The remaining checks read fields the schema guarantees; if the schema
    # failed there is nothing dependable to read.
    if any(f.severity == "error" for f in findings):
        return ValidationReport(findings=tuple(findings))

    findings.extend(_check_coverage(results))
    findings.extend(_check_marginals(results))

    range_findings, labels = _check_metric_ranges(results)
    findings.extend(range_findings)

    findings.extend(_check_receipt(results, receipt, official_digests, supported))

    return ValidationReport(findings=tuple(findings), labels=labels)


def _check_schema(results: Mapping, receipt: Mapping | None) -> tuple[Finding, ...]:
    findings = [_error("schema", problem) for problem in schema_mod.validate(results, "results")]
    if receipt is not None:
        findings.extend(
            _error("schema", f"receipt: {problem}")
            for problem in schema_mod.validate(receipt, "receipt")
        )
    return tuple(findings)


def _slots(metric_block: Mapping) -> list[tuple[str, Any]]:
    """The ten addressable slots of one metric, as (path, value) pairs."""
    slots = [(f"websites.{site}", metric_block["websites"][site]) for site in SITE_NAMES]
    slots += [(f"conditions.{c}", metric_block["conditions"][c]) for c in CONDITIONS]
    slots.append(("overall", metric_block["overall"]))
    return slots


def _check_coverage(results: Mapping) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    reasons = dict(results.get("reasons") or {})
    used_reason_keys: set[str] = set()

    for metric, block in results["metrics"].items():
        for path, value in _slots(block):
            if value is not None:
                continue
            metric_key = metric
            cell_key = f"{metric}.{path}"
            if cell_key in reasons:
                used_reason_keys.add(cell_key)
            elif metric_key in reasons:
                used_reason_keys.add(metric_key)
            else:
                findings.append(
                    _error(
                        "coverage",
                        f"{cell_key} is null but has no entry in `reasons`. Add "
                        f'"{cell_key}" (or "{metric_key}" to cover the whole metric).',
                    )
                )

    for key in sorted(set(reasons) - used_reason_keys):
        findings.append(
            _warning("coverage", f"`reasons` has an entry for {key!r} but nothing there is null.")
        )

    return tuple(findings)


def _check_marginals(results: Mapping) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    official = task_counts()

    for site, expected in official.items():
        actual = results["n"]["websites"].get(site)
        if actual != expected:
            findings.append(
                _error(
                    "marginals",
                    f"n.websites.{site} is {actual}, expected {expected}: every cell must "
                    f"cover all of that website's tasks.",
                )
            )

    for condition in CONDITIONS:
        actual = results["n"]["conditions"].get(condition)
        if actual != TOTAL_TASKS:
            findings.append(
                _error(
                    "marginals",
                    f"n.conditions.{condition} is {actual}, expected {TOTAL_TASKS} "
                    f"({' + '.join(str(v) for v in official.values())}).",
                )
            )

    for metric, block in results["metrics"].items():
        problems = metrics_mod.check_marginals(
            websites=block["websites"],
            conditions=block["conditions"],
            overall=block["overall"],
        )
        for problem in problems:
            findings.append(
                _error(
                    "marginals",
                    f"{metric}: {problem}. The overall value is the unweighted mean of the "
                    f"eighteen (website, condition) cells, so the two marginals and the "
                    f"overall must agree.",
                )
            )

    return tuple(findings)


def _check_metric_ranges(results: Mapping) -> tuple[tuple[Finding, ...], dict[str, tuple[str, ...]]]:
    """Range checks beyond the schema, plus the SFR low-confidence decision."""
    findings: list[Finding] = []
    labels: dict[str, tuple[str, ...]] = {}

    sfr_block = results["metrics"]["SFR"]
    sfr_values = {path: value for path, value in _slots(sfr_block) if value is not None}
    if not sfr_values:
        return tuple(findings), labels

    skill_calls = results["n"].get("skill_calls")
    label = str(results["submission"]["provenance"]["label"])

    if skill_calls is None:
        if label == "self-reported":
            findings.append(
                _error(
                    "metric-ranges",
                    "SFR is reported but n.skill_calls is missing. SFR rests on the number "
                    "of skill invocations behind it, and without that count the "
                    "low-confidence flag cannot be decided.",
                )
            )
        else:
            findings.append(
                _warning(
                    "metric-ranges",
                    "SFR is reported without n.skill_calls, so it is shown without a "
                    "confidence flag.",
                )
            )
        return tuple(findings), labels

    low = []
    for path in sfr_values:
        key = path.split(".")[-1] if path != "overall" else "overall"
        calls = skill_calls.get(key)
        if calls is None:
            findings.append(
                _warning("metric-ranges", f"n.skill_calls has no entry for {key!r}.")
            )
            continue
        if calls < metrics_mod.SFR_MIN_SKILL_CALLS:
            low.append(f"{key} ({calls} calls)")

    if low:
        labels["SFR"] = (LOW_CONFIDENCE_LABEL,)
        findings.append(
            _warning(
                "metric-ranges",
                f"SFR rests on fewer than {metrics_mod.SFR_MIN_SKILL_CALLS} skill "
                f"invocations for: {', '.join(sorted(low))}. These values will be marked "
                f"low-confidence and SFR cannot be used as a sort key.",
            )
        )

    return tuple(findings), labels


def _check_receipt(
    results: Mapping,
    receipt: Mapping | None,
    official_digests: Mapping[str, str] | None,
    supported: Sequence[str],
) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    label = str(results["submission"]["provenance"]["label"])
    harness_version = str(results["harness_version"])

    if harness_version not in supported:
        findings.append(
            _error(
                "receipt",
                f"harness_version {harness_version!r} is not in the supported list "
                f"{list(supported)}.",
            )
        )

    if label == "self-reported":
        if receipt is None:
            findings.append(
                _error(
                    "receipt",
                    "a self-reported entry must ship a run receipt (run `skillshift report`, "
                    "which writes run_receipt.json next to results.json).",
                )
            )
            return tuple(findings)
    else:
        if receipt is not None:
            findings.append(
                _error(
                    "receipt",
                    f"a {label!r} entry must not ship a receipt: its numbers come from a "
                    f"publication, not from a run of this harness.",
                )
            )
        return tuple(findings)

    if str(receipt["harness_version"]) != harness_version:
        findings.append(
            _error(
                "receipt",
                f"harness_version differs between results ({harness_version!r}) and receipt "
                f"({receipt['harness_version']!r}).",
            )
        )

    official = task_counts()
    for site, cells in receipt["n_per_cell"].items():
        for condition, n in cells.items():
            if n != official.get(site):
                findings.append(
                    _error(
                        "receipt",
                        f"n_per_cell.{site}.{condition} is {n}, expected {official.get(site)}.",
                    )
                )

    if official_digests is None:
        findings.append(
            _warning("receipt", "no official image digests supplied; env_digests not checked.")
        )
    else:
        for name, digest in receipt["env_digests"].items():
            expected = official_digests.get(name)
            if expected is None:
                findings.append(
                    _warning("receipt", f"env_digests names {name!r}, which is not an official image.")
                )
            elif digest != expected:
                findings.append(
                    _error(
                        "receipt",
                        f"env_digests.{name} is {digest!r}, but the official image is "
                        f"{expected!r}. The run did not use the published environment.",
                    )
                )

    if receipt["aggregate"]["metrics"] != results["metrics"]:
        findings.append(
            _error("receipt", "receipt.aggregate.metrics differs from the submitted metrics.")
        )
    if receipt["aggregate"]["n"] != results["n"]:
        findings.append(
            _error("receipt", "receipt.aggregate.n differs from the submitted n.")
        )

    return tuple(findings)
