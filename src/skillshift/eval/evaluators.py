"""base class for evaluation"""
# answer string match
import collections
import html
import importlib
import json
import time
import urllib
from pathlib import Path
from typing import Any, Tuple, Union

from beartype import beartype
from playwright.sync_api import CDPSession, Page

from webarena.browser_env.actions import Action
from webarena.browser_env.utils import StateInfo
from webarena.evaluation_harness.helper_functions import PseudoPage

from .llm_judge import judge, judge_unachievable

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


class URLEvaluator(Evaluator):
    """Check URL matching"""

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

        def clean_url(url: str) -> str:
            url = str(url)
            url = url.rstrip("/")
            return url

        def parse_url(url: str) -> tuple[str, dict[str, list[str]]]:
            """Parse a URL into its base, path, and query components."""
            parsed_url = urllib.parse.urlparse(url)
            base_path = parsed_url.netloc + parsed_url.path
            query = urllib.parse.parse_qs(parsed_url.query)
            return base_path, query

        def parse_urls(
            urls: list[str],
        ) -> tuple[list[str], dict[str, set[str]]]:
            """Parse a list of URLs."""
            base_paths = []
            queries = collections.defaultdict(set)
            for url in urls:
                base_path, query = parse_url(url)
                base_paths.append(base_path)
                for k, v in query.items():
                    queries[k].update(v)
            return base_paths, queries

        pred = clean_url(page.url)
        ref_urls = configs["eval"]["reference_url"].split(" |OR| ")
        ref_urls = [clean_url(url) for url in ref_urls]
        matching_rule = configs["eval"].get("url_note", "GOLD in PRED")
        if matching_rule == "GOLD in PRED":
            ref_base_paths, ref_queries = parse_urls(ref_urls)
            pred_base_paths, pred_query = parse_url(pred)

            base_score = float(
                any(
                    [
                        ref_base_path in pred_base_paths
                        for ref_base_path in ref_base_paths
                    ]
                )
            )
            query_score = 1.0
            for k, possible_values in ref_queries.items():
                query_score *= float(
                    any(
                        possible_ref_value in pred_query.get(k, [])
                        for possible_ref_value in possible_values
                    )
                )
            score = base_score * query_score

        else:
            raise ValueError(f"Unknown matching rule: {matching_rule}")

        return score


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
            print(f"selected element: {selected_element}")

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
        print(f"score: {score}")
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
