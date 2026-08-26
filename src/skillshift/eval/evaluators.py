"""base class for evaluation"""
# answer string match
import collections
import html
import importlib
import json
import logging
import re
import time
import urllib
from pathlib import Path
from typing import Any, Tuple, Union

from beartype import beartype
from playwright.sync_api import CDPSession, Page

from webarena.browser_env.actions import Action
from webarena.browser_env.utils import StateInfo
# `HTMLContentEvaluator` resolves a `func:name(...)` locator with a bare
# `eval()`, which looks the name up in *this module's* globals.  Importing only
# PseudoPage meant every task whose evaluation calls a helper died with
# NameError -- 24 of the shipped tasks call gitlab_get_project_memeber_role
# (upstream's typo, kept verbatim because the task files reference it).
#
# This is the same import WebArena's own evaluators.py makes, so a `func:`
# locator resolves here exactly as it does upstream.
from webarena.evaluation_harness.helper_functions import (  # noqa: F401 - resolved by eval()
    PseudoPage,
    gitlab_get_project_memeber_role,
    llm_fuzzy_match,
    llm_ua_match,
    reddit_get_post_url,
    shopping_get_latest_order_url,
    shopping_get_sku_latest_review_author,
    shopping_get_sku_latest_review_rating,
)

from .llm_judge import judge, judge_unachievable

logger = logging.getLogger(__name__)

Trajectory = list[Union[Action, StateInfo]]


class Evaluator(object):
    def __init__(self, eval_tag: str = "") -> None:
        self.eval_tag = eval_tag

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | PseudoPage,
        client: CDPSession,
    ) -> float:
        raise NotImplementedError

    @staticmethod
    def get_last_action(trajectory: Trajectory) -> Action:
        try:
            # is_bearable(trajectory[-1], Action)
            last_action = trajectory[-1]
        except Exception:
            raise ValueError(
                "The last element of trajectory should be an action, add a fake stop action if needed"
            )

        return last_action  # type: ignore[return-value]

    @staticmethod
    def get_last_state(trajectory: Trajectory) -> StateInfo:
        try:
            # is_bearable(trajectory[-2], StateInfo)
            last_state = trajectory[-2]
        except Exception:
            raise ValueError(
                "The second last element of trajectory should be a state, add a fake stop action if needed"
            )

        return last_state  # type: ignore[return-value]


class StringEvaluator(Evaluator):
    """Check whether the answer is correct by asking a configurable LLM judge.

    The reference answers in the task config are still expressed with the
    ``exact_match`` / ``must_include`` / ``fuzzy_match`` keys, but instead of
    doing literal string comparison we let an LLM decide whether the agent's
    answer conveys the same information as the reference. This tolerates
    differences in wording, formatting, ordering, casing and units that the old
    literal matcher rejected. See ``llm_judge.py`` for API configuration.
    """

    @staticmethod
    @beartype
    def clean_answer(answer: str) -> str:
        """Strip surrounding quotes/whitespace before handing to the judge."""
        answer = answer.strip()
        if answer.startswith("'") and answer.endswith("'"):
            answer = answer[1:-1]
        elif answer.startswith('"') and answer.endswith('"'):
            answer = answer[1:-1]
        return answer

    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | PseudoPage | None = None,
        client: CDPSession | None = None,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        intent = configs["intent"]
        last_action = self.get_last_action(trajectory)
        pred = self.clean_answer(last_action["answer"])

        score = 1.0
        for approach, value in configs["eval"]["reference_answers"].items():
            match approach:
                case "exact_match":
                    score *= judge(intent, [value], pred, mode="exact")

                case "must_include":
                    assert isinstance(value, list)
                    score *= judge(intent, value, pred, mode="include_all")

                case "fuzzy_match":
                    if value == "N/A":
                        # The task is unachievable. A bare "N/A" answer already
                        # counts as correct; otherwise ask the LLM whether the
                        # answer recognizes the task as infeasible with a valid
                        # reason.
                        if pred.strip().upper() == "N/A":
                            score *= 1.0
                        else:
                            score *= judge_unachievable(
                                intent,
                                configs["eval"]["string_note"],
                                pred,
                            )
                    else:
                        assert isinstance(value, list)
                        score *= judge(intent, value, pred, mode="fuzzy")
        return score


def _clean_url(url: str) -> str:
    return str(url).rstrip("/")


def _parse_url(url: str) -> tuple[str, dict[str, list[str]]]:
    """Parse a URL into its base-path and query components."""
    parsed_url = urllib.parse.urlparse(url)
    base_path = parsed_url.netloc + parsed_url.path
    query = urllib.parse.parse_qs(parsed_url.query)
    return base_path, query


def _parse_urls(urls: list[str]) -> tuple[list[str], dict[str, set[str]]]:
    """Parse a list of URLs, merging their query values by key."""
    base_paths = []
    queries: dict[str, set[str]] = collections.defaultdict(set)
    for url in urls:
        base_path, query = _parse_url(url)
        base_paths.append(base_path)
        for k, v in query.items():
            queries[k].update(v)
    return base_paths, queries


def _url_match_score(pred: str, ref_urls: list[str]) -> float:
    """"GOLD in PRED": pred's base path contains one of the gold base paths,
    and pred's query carries every value the gold query requires."""
    ref_base_paths, ref_queries = _parse_urls(ref_urls)
    pred_base_path, pred_query = _parse_url(pred)

    base_score = float(any(ref_base_path in pred_base_path for ref_base_path in ref_base_paths))
    query_score = 1.0
    for key, possible_values in ref_queries.items():
        query_score *= float(
            any(possible_ref_value in pred_query.get(key, []) for possible_ref_value in possible_values)
        )
    return base_score * query_score


_CANONICAL_LINK_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', re.IGNORECASE
)


def _canonical_of_loaded_page(page: Page | PseudoPage) -> str | None:
    """The canonical URL the page currently open in `page` declares for itself.

    Read from the already-rendered DOM -- no navigation, no network call.
    """
    try:
        href = page.evaluate("() => document.querySelector('link[rel=\"canonical\"]')?.href || null")
    except Exception:  # noqa: BLE001 - a page stand-in without this is a no-op, not a crash
        return None
    return str(href) if href else None


def _canonical_of_url(page: Page | PseudoPage, url: str) -> str | None:
    """Fetch `url` out-of-band -- via the browser context's own request API,
    so this never navigates the agent's page or opens a visible tab -- and
    read the canonical link its response declares."""
    try:
        response = page.context.request.get(url, timeout=10_000)
        if not response.ok:
            return None
        html_text = response.text()
    except Exception:  # noqa: BLE001 - the fallback degrades to "no match", not a crash
        return None
    match = _CANONICAL_LINK_RE.search(html_text)
    return match.group(1) if match else None


class URLEvaluator(Evaluator):
    """Check URL matching, with a canonical-URL fallback for equivalent forms.

    A CMS can serve one resource under more than one URL -- WordPress's
    `?cat=46` and `/category/politics/` both resolve to the same category
    archive -- and the literal base-path/query check below cannot see that.
    A real trajectory run (skillshift.wordpress.26 and .52, 2026-08-26) showed
    the reference agent reaching the exact right page by its pretty-permalink
    form and scoring 0 anyway, because the gold answer was written as a query
    string. When the literal check fails, this falls back to asking the page
    itself: WordPress renders the same `<link rel="canonical">` regardless of
    which URL form was requested, so comparing canonical forms recognizes the
    equivalence without hardcoding a slug/id lookup table.
    """

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | PseudoPage,
        client: CDPSession | None = None,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        matching_rule = configs["eval"].get("url_note", "GOLD in PRED")
        if matching_rule != "GOLD in PRED":
            raise ValueError(f"Unknown matching rule: {matching_rule}")

        pred = _clean_url(page.url)
        ref_urls = [_clean_url(url) for url in configs["eval"]["reference_url"].split(" |OR| ")]

        score = _url_match_score(pred, ref_urls)
        if score > 0.0:
            return score

        canonical_pred = _canonical_of_loaded_page(page)
        if not canonical_pred:
            return 0.0
        canonical_refs = [
            canonical for url in ref_urls if (canonical := _canonical_of_url(page, url)) is not None
        ]
        if not canonical_refs:
            return 0.0
        return _url_match_score(_clean_url(canonical_pred), [_clean_url(url) for url in canonical_refs])


class HTMLContentEvaluator(Evaluator):
    """Check whether the contents appear in the page"""

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | PseudoPage,
        client: CDPSession | None = None,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        intent = configs.get("intent", "")
        targets = configs["eval"]["program_html"]

        score = 1.0
        for target in targets:
            target_url: str = target["url"]  # which url to check
            if target_url.startswith("func"):
                func = target_url.split("func:")[1]
                func = func.replace("__last_url__", page.url)
                target_url = eval(func)

            locator: str = target["locator"]  # js element locator

            # navigate to that url
            prev_page = None
            if target_url != "last":
                prev_page = page
                page = page.context.new_page()
                page.goto(target_url, wait_until='domcontentloaded', timeout=60000)
                time.sleep(3)  # TODO [shuyanzh]: fix this hard-coded sleep

            # empty, use the full page
            if not locator.strip():
                selected_element = page.content()
            # use JS to select the element
            elif locator.startswith("document.") or locator.startswith(
                "[...document."
            ):
                if "prep_actions" in target:
                    try:
                        for prep_action in target["prep_actions"]:
                            page.evaluate(f"() => {prep_action}")
                    except Exception:
                        pass
                try:
                    selected_element = str(page.evaluate(f"() => {locator}"))
                    if not selected_element:
                        selected_element = ""
                except Exception:
                    # the page is wrong, return empty
                    selected_element = ""
            # run program to call API
            elif locator.startswith("func:"):  # a helper function
                func = locator.split("func:")[1]
                func = func.replace("__page__", "page")
                selected_element = eval(func)
            else:
                raise ValueError(f"Unknown locator: {locator}")

            selected_element = html.unescape(selected_element)
            # Was a bare `print` of the whole selected element, inherited from
            # WebArena. On a non-blocking stdout -- which is what a pipe under
            # tmux gives you -- writing a page-sized string raises
            # BlockingIOError, and because this runs inside the evaluator the
            # exception kills the task. One run of the reference sweep was lost
            # to it. A debug print must never be able to destroy a measurement.
            logger.debug("selected element: %s", selected_element)

            if "exact_match" in target["required_contents"]:
                required_contents = target["required_contents"]["exact_match"]
                cur_score = judge(
                    intent,
                    [required_contents],
                    selected_element,
                    mode="exact",
                    subject="the page content",
                )
                score *= float(cur_score)
                # print(f"[exact match] {cur_score}, selected element: {selected_element}, required contents: {required_contents}")
            elif "must_include" in target["required_contents"]:
                required_contents = target["required_contents"]["must_include"]
                assert isinstance(required_contents, list)
                for content in required_contents:
                    # Each entry may list interchangeable alternatives with
                    # " |OR| "; any one of them satisfies the requirement.
                    content_or = content.split(" |OR| ")
                    cur_score = judge(
                        intent,
                        content_or,
                        selected_element,
                        mode="include_any",
                        subject="the page content",
                    )
                    score *= float(cur_score)
                    # print(f"[must include] {cur_score}, selected element: {selected_element}, required contents: {content_or}")
            else:
                raise ValueError(
                    f"Unknown required_contents: {target['required_contents'].keys()}"
                )

            if prev_page:
                page.close()
                page = prev_page
                prev_page = None

        return score


class EvaluatorComb:
    def __init__(self, evaluators: list[Evaluator]) -> None:
        self.evaluators = evaluators

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | PseudoPage,
        client: CDPSession | None,
    ) -> float:
        score = 1.0
        for evaluator in self.evaluators:
            cur_score = evaluator(trajectory, config_file, page, client)
            score *= cur_score
        logger.debug("score: %s", score)
        return score


@beartype
def evaluator_router(config_file: Path | str) -> EvaluatorComb:
    """Router to get the evaluator class"""
    with open(config_file, "r") as f:
        configs = json.load(f)

    eval_types = configs["eval"]["eval_types"]
    evaluators: list[Evaluator] = []
    for eval_type in eval_types:
        match eval_type:
            case "string_match":
                evaluators.append(StringEvaluator())
            case "url_match":
                evaluators.append(URLEvaluator())
            case "program_html":
                evaluators.append(HTMLContentEvaluator())
            case _:
                raise ValueError(f"eval_type {eval_type} is not supported")

    return EvaluatorComb(evaluators)
