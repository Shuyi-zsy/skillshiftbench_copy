"""`URLEvaluator`: exact query-string matching, plus a canonical-URL fallback.

WordPress (and other CMSes) can serve the identical resource under more than
one URL -- a numeric query string (`?cat=46`) and a pretty permalink
(`/category/politics/`) both resolve to the same category archive. The
original "GOLD in PRED" check is a literal base-path/query comparison and
cannot see that equivalence: a real trajectory run (skillshift.wordpress.26
and .52, 2026-08-26) showed the reference agent navigating to the exact
right page by its pretty-permalink form and being scored 0 anyway, because
the gold answer was written as a query string.

The fallback added here reads the page's own `<link rel="canonical">` --
which a CMS renders consistently no matter which URL form was requested --
rather than hardcoding a slug/id lookup table, so it generalizes to any
pretty-permalink family instead of just category/tag.

No dedicated test file existed for this module before (grep confirms); this
is the first.
"""

from __future__ import annotations

import json

import pytest

webarena_env = pytest.importorskip("webarena.browser_env.env_config")

from webarena.evaluation_harness.helper_functions import PseudoPage  # noqa: E402

from skillshift.eval.evaluators import URLEvaluator  # noqa: E402


class FakeResponse:
    def __init__(self, *, ok: bool, text: str = ""):
        self.ok = ok
        self._text = text

    def text(self) -> str:
        return self._text


class FakeRequestContext:
    """Stands in for Playwright's `BrowserContext.request` (out-of-band GET,
    no navigation, no new tab)."""

    def __init__(self, responses: dict[str, FakeResponse] | None = None):
        self._responses = responses or {}
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: float | None = None) -> FakeResponse:
        self.requested_urls.append(url)
        return self._responses.get(url, FakeResponse(ok=False))


class FakeContext:
    def __init__(self, responses=None):
        self.request = FakeRequestContext(responses)


class _InnerFakePage:
    """The object a `PseudoPage` delegates every attribute but `url` to."""

    def __init__(self, *, canonical: str | None = None, responses=None, evaluate_raises=False):
        self._canonical = canonical
        self._evaluate_raises = evaluate_raises
        self.context = FakeContext(responses)

    def evaluate(self, _script: str):
        if self._evaluate_raises:
            raise RuntimeError("page was closed")
        return self._canonical


def fake_page(url: str, *, canonical: str | None = None, responses=None, evaluate_raises=False) -> PseudoPage:
    """A `PseudoPage` (the real type `URLEvaluator` accepts) wrapping a fake."""
    inner = _InnerFakePage(canonical=canonical, responses=responses, evaluate_raises=evaluate_raises)
    return PseudoPage(original_page=inner, url=url)


def write_config(tmp_path, *, reference_url: str, url_note: str = "GOLD in PRED"):
    path = tmp_path / "task.json"
    path.write_text(
        json.dumps({"eval": {"eval_types": ["url_match"], "reference_url": reference_url, "url_note": url_note}})
    )
    return path


def score(tmp_path, *, reference_url: str, page, url_note: str = "GOLD in PRED") -> float:
    config = write_config(tmp_path, reference_url=reference_url, url_note=url_note)
    return URLEvaluator()([], config, page, None)


class TestExactMatchIsUnchanged:
    def test_a_matching_query_string_scores_one(self, tmp_path):
        page = fake_page("http://localhost:8000/?cat=46")
        assert score(tmp_path, reference_url="http://localhost:8000/?cat=46", page=page) == 1.0

    def test_the_canonical_fallback_is_not_consulted_on_a_match(self, tmp_path):
        # If the fast path already scored 1.0, nothing should call out to
        # `.context.request` at all -- the fallback only exists for the 0 case.
        page = fake_page("http://localhost:8000/?cat=46", canonical="http://should-not-be-read.invalid/")
        assert score(tmp_path, reference_url="http://localhost:8000/?cat=46", page=page) == 1.0
        assert page.context.request.requested_urls == []

    def test_a_different_query_value_still_scores_zero(self, tmp_path):
        page = fake_page("http://localhost:8000/?cat=99")
        assert score(tmp_path, reference_url="http://localhost:8000/?cat=46", page=page) == 0.0

    def test_an_unrelated_page_scores_zero(self, tmp_path):
        page = fake_page("http://localhost:8000/")
        assert score(tmp_path, reference_url="http://localhost:8000/?cat=46", page=page) == 0.0


class TestCanonicalFallback:
    def test_a_pretty_permalink_matching_the_golds_canonical_scores_one(self, tmp_path):
        # The agent lands on /category/politics/ (its own canonical). Gold is
        # written as ?cat=46, which WordPress itself canonicalizes to the same
        # pretty-permalink URL when fetched out-of-band.
        page = fake_page(
            "http://localhost:8000/category/politics/",
            canonical="http://localhost:8000/category/politics/",
            responses={
                "http://localhost:8000/?cat=46": FakeResponse(
                    ok=True,
                    text='<link rel="canonical" href="http://localhost:8000/category/politics/" />',
                )
            },
        )
        result = score(tmp_path, reference_url="http://localhost:8000/?cat=46", page=page)
        assert result == 1.0

    def test_a_genuinely_wrong_page_still_scores_zero(self, tmp_path):
        page = fake_page(
            "http://localhost:8000/category/business/",
            canonical="http://localhost:8000/category/business/",
            responses={
                "http://localhost:8000/?cat=46": FakeResponse(
                    ok=True,
                    text='<link rel="canonical" href="http://localhost:8000/category/politics/" />',
                )
            },
        )
        assert score(tmp_path, reference_url="http://localhost:8000/?cat=46", page=page) == 0.0

    def test_a_site_with_no_canonical_tag_falls_through_to_zero(self, tmp_path):
        page = fake_page("http://localhost:8000/category/politics/", canonical=None)
        assert score(tmp_path, reference_url="http://localhost:8000/?cat=46", page=page) == 0.0

    def test_a_failed_out_of_band_fetch_falls_through_to_zero_not_a_crash(self, tmp_path):
        page = fake_page(
            "http://localhost:8000/category/politics/",
            canonical="http://localhost:8000/category/politics/",
            responses={"http://localhost:8000/?cat=46": FakeResponse(ok=False)},
        )
        assert score(tmp_path, reference_url="http://localhost:8000/?cat=46", page=page) == 0.0

    def test_a_page_that_cannot_report_its_own_canonical_is_a_safe_no_op(self, tmp_path):
        # A page stand-in that raises on evaluate() (e.g. it was already
        # closed) must not take the whole evaluation down with it.
        page = fake_page("http://localhost:8000/category/politics/", evaluate_raises=True)
        assert score(tmp_path, reference_url="http://localhost:8000/?cat=46", page=page) == 0.0

    def test_multiple_or_separated_reference_urls_are_each_tried(self, tmp_path):
        page = fake_page(
            "http://localhost:8000/tag/javascript/",
            canonical="http://localhost:8000/tag/javascript/",
            responses={
                "http://localhost:8000/?cat=1": FakeResponse(
                    ok=True, text='<link rel="canonical" href="http://localhost:8000/category/other/" />'
                ),
                "http://localhost:8000/?tag=javascript": FakeResponse(
                    ok=True, text='<link rel="canonical" href="http://localhost:8000/tag/javascript/" />'
                ),
            },
        )
        result = score(
            tmp_path,
            reference_url="http://localhost:8000/?cat=1 |OR| http://localhost:8000/?tag=javascript",
            page=page,
        )
        assert result == 1.0
