"""Reading a directory of submissions and rendering the leaderboard preview.

The leaderboard repository stores one JSON file per entry and lets CI do the
talking: `skillshift validate` decides whether a pull request is admissible, and
this module renders what the reviewer sees -- where the entry would land, its
full breakdown, and which labels it should carry.

Two rules from `docs/results-policy.md` are enforced here in code rather than in
the renderer's good intentions:

* **SR is the primary key, and SFR is never a sort key.**  At the skill-call
  rates the paper measures (ASC 0.06-0.15), SFR's denominator is a handful of
  invocations per cell; sorting on it would rank noise.
* **A thin SFR is marked.**  The threshold is
  `metrics.SFR_MIN_SKILL_CALLS` -- imported, not restated.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .conditions import CONDITIONS
from .errors import ValidationError
from .eval.metrics import METRIC_NAMES, SFR_MIN_SKILL_CALLS
from .sites import SITE_NAMES

#: The metric the leaderboard is ordered by.
PRIMARY_METRIC = "SR"

#: Metrics a reader may re-sort on.  SFR is deliberately absent.
SORTABLE_METRICS: tuple[str, ...] = ("SR", "AS", "ASC")

#: Fewer skill invocations than this behind an SFR value and it is marked.
LOW_CONFIDENCE_THRESHOLD = SFR_MIN_SKILL_CALLS

LOW_CONFIDENCE_MARK = "⚠︎"

RECEIPT_SUFFIX = ".receipt.json"

SORT_KEY_NOTE = (
    f"`SFR` is a diagnostic, never a sort key: at the skill-call rates this benchmark "
    f"measures, a cell resting on fewer than {LOW_CONFIDENCE_THRESHOLD} invocations is "
    f"marked {LOW_CONFIDENCE_MARK} and means very little on its own. The leaderboard "
    f"orders by `{PRIMARY_METRIC}`."
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")


@dataclass(frozen=True)
class SubmissionName:
    """The three parts of a conforming submission filename."""

    date: str
    method: str
    model: str


def parse_filename(name: str) -> SubmissionName:
    """Parse `YYYY-MM-DD--<method>--<model>.json`, or say exactly what is wrong."""
    text = Path(str(name)).name
    if text.endswith(RECEIPT_SUFFIX):
        raise ValidationError(f"{text!r} is a receipt, not a submission.")
    stem, _, extension = text.rpartition(".")
    if extension != "json" or not stem:
        raise ValidationError(f"{text!r} must end in '.json'.")

    parts = stem.split("--")
    if len(parts) != 3:
        raise ValidationError(
            f"{text!r} must be named 'YYYY-MM-DD--<method>--<model>.json'; got "
            f"{len(parts)} '--'-separated part(s) instead of 3."
        )

    date, method, model = parts
    if not _DATE_RE.match(date):
        raise ValidationError(f"{text!r} does not start with a YYYY-MM-DD date.")
    for label, slug in (("method", method), ("model", model)):
        if not _SLUG_RE.match(slug):
            raise ValidationError(
                f"{text!r}: the {label} part {slug!r} must be lower-case letters, digits, "
                f"'-' and '.' only, and may not contain '--'."
            )
    return SubmissionName(date=date, method=method, model=model)


def receipt_path_for(results_path: Path | str) -> Path:
    """The receipt that belongs beside a results file."""
    path = Path(results_path)
    return path.with_name(path.name[: -len(".json")] + RECEIPT_SUFFIX)


def check_filename(path: Path | str, results: Mapping) -> tuple[str, ...]:
    """Problems with a submission's filename, given its contents."""
    path = Path(path)
    try:
        parsed = parse_filename(path.name)
    except ValidationError as exc:
        return (str(exc),)

    declared = str(results.get("submission", {}).get("date", ""))
    if declared != parsed.date:
        return (
            f"{path.name}: the filename date {parsed.date!r} differs from "
            f"submission.date {declared!r}.",
        )
    return ()


def _slots(block: Mapping) -> tuple[tuple[str, object], ...]:
    """The ten addressable slots of one metric, keyed the way `n.skill_calls` is."""
    return (
        *((site, block["websites"][site]) for site in SITE_NAMES),
        *((condition, block["conditions"][condition]) for condition in CONDITIONS),
        ("overall", block["overall"]),
    )


@dataclass(frozen=True)
class Entry:
    """One leaderboard entry: a results file and its optional receipt."""

    path: Path | None
    results: Mapping
    receipt: Mapping | None = None

    @property
    def name(self) -> str:
        return str(self.results["submission"]["name"])

    @property
    def model_id(self) -> str:
        return str(self.results["submission"]["model"]["id"])

    @property
    def label(self) -> str:
        return str(self.results["submission"]["provenance"]["label"])

    @property
    def source(self) -> str:
        return str(self.results["submission"]["provenance"]["source"])

    def block(self, metric: str) -> Mapping:
        return self.results["metrics"][metric]

    def overall(self, metric: str) -> float | None:
        return self.block(metric)["overall"]

    def skill_calls(self) -> Mapping[str, int]:
        return dict(self.results.get("n", {}).get("skill_calls") or {})

    def low_confidence_slots(self) -> tuple[str, ...]:
        """SFR slots resting on too few skill invocations to be worth reading."""
        calls = self.skill_calls()
        if not calls:
            return ()
        return tuple(
            key
            for key, value in _slots(self.block("SFR"))
            if value is not None
            and calls.get(key) is not None
            and calls[key] < LOW_CONFIDENCE_THRESHOLD
        )

    def format(self, metric: str, slot: str = "overall") -> str:
        """One rendered cell, carrying the low-confidence mark where it belongs."""
        values = dict(_slots(self.block(metric)))
        value = values.get(slot)
        if value is None:
            return "--"
        text = f"{float(value):.2f}"
        if metric == "SFR" and slot in self.low_confidence_slots():
            return f"{text} {LOW_CONFIDENCE_MARK}"
        return text


def load_entry(results_path: Path | str) -> Entry:
    """Load one submission, picking up its receipt if one sits beside it."""
    path = Path(results_path)
    try:
        results = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path} is not valid JSON: {exc}") from exc

    receipt_path = receipt_path_for(path)
    receipt = None
    if receipt_path.is_file():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{receipt_path} is not valid JSON: {exc}") from exc

    return Entry(path=path, results=results, receipt=receipt)


def load_entries(directory: Path | str) -> tuple[Entry, ...]:
    """Every submission in a directory, receipts excluded from the listing."""
    directory = Path(directory)
    if not directory.is_dir():
        raise ValidationError(f"Submissions directory not found: {directory}")
    paths = sorted(p for p in directory.glob("*.json") if not p.name.endswith(RECEIPT_SUFFIX))
    return tuple(load_entry(path) for path in paths)


def rank(entries: Sequence[Entry], *, metric: str = PRIMARY_METRIC) -> tuple[Entry, ...]:
    """Order entries best-first.  Entries without a value for the metric sort last."""
    if metric not in SORTABLE_METRICS:
        if metric in METRIC_NAMES:
            raise ValidationError(
                f"{metric!r} cannot order the leaderboard. {SORT_KEY_NOTE}"
            )
        raise ValidationError(f"Unknown metric {metric!r}. Expected one of {list(METRIC_NAMES)}.")

    #: AS is a cost: lower is better.  SR and ASC are higher-is-better.
    descending = metric != "AS"

    def key(entry: Entry):
        value = entry.overall(metric)
        if value is None:
            return (1, 0.0, entry.name)
        return (0, -value if descending else value, entry.name)

    return tuple(sorted(entries, key=key))


def suggest_labels(entry: Entry) -> tuple[str, ...]:
    """The labels the leaderboard should render next to this entry."""
    labels = [entry.label]
    if entry.low_confidence_slots():
        labels.append("low-confidence SFR")
    if entry.results["submission"]["method"].get("code_url") is None:
        labels.append("code not released")
    return tuple(labels)


def _ranking_table(entries: Sequence[Entry], highlight: Entry | None) -> list[str]:
    lines = [
        "| # | Method | Model | SR | AS | ASC | SFR | Source |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for position, entry in enumerate(rank(entries), start=1):
        marker = " **<-- this PR**" if highlight is not None and entry.name == highlight.name else ""
        cells = " | ".join(entry.format(metric) for metric in METRIC_NAMES)
        lines.append(
            f"| {position} | {entry.name}{marker} | `{entry.model_id}` | {cells} | {entry.label} |"
        )
    return lines


def _breakdown_table(entry: Entry) -> list[str]:
    columns = (*SITE_NAMES, *CONDITIONS, "overall")
    lines = [
        "| Metric | " + " | ".join(columns) + " |",
        "| --- |" + " ---: |" * len(columns),
    ]
    for metric in METRIC_NAMES:
        cells = " | ".join(entry.format(metric, slot) for slot in columns)
        lines.append(f"| {metric} | {cells} |")
    return lines


def _low_confidence_note(entry: Entry) -> list[str]:
    slots = entry.low_confidence_slots()
    if not slots:
        return []
    calls = entry.skill_calls()
    detail = ", ".join(f"`{slot}` ({calls[slot]} skill calls)" for slot in slots)
    return [
        "",
        f"{LOW_CONFIDENCE_MARK} **SFR low confidence** for {detail} "
        f"-- fewer than {LOW_CONFIDENCE_THRESHOLD} invocations behind the ratio.",
    ]


def render_preview(entries: Sequence[Entry], new_entry: Entry, report=None) -> str:
    """The markdown a leaderboard pull request gets as a comment."""
    filename = new_entry.path.name if new_entry.path else new_entry.name
    lines = [f"## Submission preview: `{filename}`", ""]

    if report is not None:
        lines += [f"**Validation: {report.summary()}**", ""]
        if report.findings:
            lines += ["<details><summary>Findings</summary>", ""]
            lines += [f"- {finding}" for finding in report.findings]
            lines += ["", "</details>", ""]

    lines += ["### Ranking preview", "", *_ranking_table(entries, new_entry), ""]
    lines += [f"### Breakdown -- {new_entry.name}", "", *_breakdown_table(new_entry)]
    lines += _low_confidence_note(new_entry)
    lines += [
        "",
        "### Suggested labels",
        "",
        *(f"- `{label}`" for label in suggest_labels(new_entry)),
        "",
        f"> {SORT_KEY_NOTE}",
        "",
        f"> Source: {new_entry.source}.",
    ]
    return "\n".join(lines) + "\n"
