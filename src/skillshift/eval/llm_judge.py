"""LLM-based judge for the WebArena evaluators.

Replaces the rigid literal string / HTML matching with a semantic judgment made
by a configurable, OpenAI-compatible LLM. Everything is configured through
environment variables so no secrets live in the codebase::

    export my_api_key="sk-..."
    export my_base_url="https://api.openai.com/v1"
    export my_model="gpt-5-mini-2025-08-07"

The judge decides whether an agent's answer (or a scraped page fragment) conveys
the same essential information as the reference answer, tolerating differences in
wording, formatting, ordering, casing, or extra irrelevant detail.
"""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Sequence

from .trajectory import TokenUsage

# --- Environment variable names (public API config) --------------------------
API_KEY_ENV = "my_api_key"
BASE_URL_ENV = "my_base_url"
MODEL_ENV = "my_model"

# --- Tuning constants --------------------------------------------------------
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 120.0

_VERDICT_RE = re.compile(r"verdict\s*[:\-]?\s*(correct|incorrect)", re.IGNORECASE)

# Cache the client and resolved model so we build them once per process.
_client = None
_model: str | None = None
_client_lock = threading.Lock()

# Token usage from every judged call since the last drain. A runner reads this
# right after the `env.step()` that may have triggered judging, so it can
# attach the spend to that step's trajectory entry -- see runner.run_task.
_usage_log: list[TokenUsage] = []
_usage_lock = threading.Lock()


def _record_usage(response) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    with _usage_lock:
        _usage_log.append(
            TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
        )


def drain_usage() -> tuple[TokenUsage, ...]:
    """Return and clear every judge call's usage recorded since the last drain."""
    with _usage_lock:
        drained = tuple(_usage_log)
        _usage_log.clear()
    return drained


def _load_config() -> tuple[str, str, str]:
    """Read the API config from the environment, failing fast if incomplete."""
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    base_url = os.environ.get(BASE_URL_ENV, "").strip()
    model = os.environ.get(MODEL_ENV, "").strip()

    missing = [
        name
        for name, value in (
            (API_KEY_ENV, api_key),
            (BASE_URL_ENV, base_url),
            (MODEL_ENV, model),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "LLM judge is not configured. Missing environment variable(s): "
            f"{', '.join(missing)}. Set {API_KEY_ENV}, {BASE_URL_ENV} and "
            f"{MODEL_ENV} before running the evaluation."
        )
    return api_key, base_url, model


def _get_client():
    """Lazily build and cache the OpenAI-compatible client."""
    global _client, _model
    if _client is not None:
        return _client, _model

    with _client_lock:
        if _client is None:
            from openai import OpenAI  # imported lazily to keep import cheap

            api_key, base_url, model = _load_config()
            _client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            _model = model
    return _client, _model


def _parse_verdict(text: str) -> float:
    """Map the model's reply to a 1.0 (correct) / 0.0 (incorrect) score."""
    matches = _VERDICT_RE.findall(text or "")
    if matches:
        return 0.0 if matches[-1].lower() == "incorrect" else 1.0

    # Fallback: look at the raw text if the model ignored the format.
    lowered = (text or "").lower()
    if "incorrect" in lowered:
        return 0.0
    if "correct" in lowered:
        return 1.0
    # Unparseable output is treated as a failed match rather than crashing.
    return 0.0


def _ask(system_prompt: str, user_prompt: str) -> float:
    """Send one judging request and return its score, with retries."""
    client, model = _get_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            _record_usage(response)
            content = response.choices[0].message.content or ""
            return _parse_verdict(content)
        except Exception as error:  # network / API errors -> retry
            last_error = error
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))

    raise RuntimeError(
        f"LLM judge request failed after {MAX_RETRIES} attempts: {last_error}"
    ) from last_error


# --- Prompt building ---------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a strict but fair evaluator for a web-agent benchmark. You are "
    "given a task instruction, one or more reference (gold) answers, and the "
    "candidate text produced by the agent. Decide whether the candidate "
    "satisfies the requirement.\n"
    "The candidate is CORRECT when it conveys the same essential information as "
    "the reference, even if wording, formatting, ordering, capitalization, "
    "units, or level of detail differ. Additional irrelevant text is fine as "
    "long as the required information is present and not contradicted.\n"
    "The candidate is INCORRECT when required information is missing, wrong, or "
    "contradicted.\n"
    "Reply with one short sentence of reasoning, then a final line exactly in "
    "the form 'VERDICT: CORRECT' or 'VERDICT: INCORRECT'."
)

_REQUIREMENT_BY_MODE = {
    "exact": "The candidate must state the same value/answer as the reference below.",
    "include_all": "The candidate must contain the information of EVERY reference item below.",
    "include_any": "The candidate must contain the information of AT LEAST ONE reference item below.",
    "fuzzy": "The candidate must be semantically equivalent to (a paraphrase of) the reference below.",
}


def _format_references(references: Sequence[str]) -> str:
    return "\n".join(f"  - {ref}" for ref in references)


def judge(
    intent: str,
    references: Sequence[str],
    response: str,
    *,
    mode: str = "include_all",
    subject: str = "the agent's answer",
) -> float:
    """Judge whether ``response`` satisfies ``references`` for the given task.

    ``mode`` selects the strictness of the requirement: one of ``exact``,
    ``include_all``, ``include_any`` or ``fuzzy``. Returns 1.0 on match, 0.0
    otherwise.
    """
    if mode not in _REQUIREMENT_BY_MODE:
        raise ValueError(f"Unknown judge mode: {mode}")

    references = [str(ref) for ref in references if str(ref).strip()]
    if not references:
        return 1.0
    # An empty candidate can never satisfy a non-empty requirement.
    if not (response or "").strip():
        return 0.0

    user_prompt = (
        f"Task instruction:\n{intent}\n\n"
        f"Requirement: {_REQUIREMENT_BY_MODE[mode]}\n\n"
        f"Reference answer(s):\n{_format_references(references)}\n\n"
        f"Candidate ({subject}):\n{response}"
    )
    return _ask(_SYSTEM_PROMPT, user_prompt)


_UNACHIEVABLE_SYSTEM_PROMPT = (
    "You are an evaluator for a web-agent benchmark. Some tasks are impossible "
    "to accomplish, and the agent is expected to report that the task is "
    "unachievable and explain a valid reason. You are given the task "
    "instruction, the reference reason describing why the task cannot be done, "
    "and the agent's response.\n"
    "The response is CORRECT when it recognizes the task as unachievable/"
    "infeasible AND gives a reason consistent with the reference reason. It is "
    "INCORRECT when it claims success, invents data, or gives a reason that "
    "conflicts with the reference.\n"
    "Reply with one short sentence of reasoning, then a final line exactly in "
    "the form 'VERDICT: CORRECT' or 'VERDICT: INCORRECT'."
)


def judge_unachievable(intent: str, reference_reason: str, response: str) -> float:
    """Judge an 'unachievable task' answer against the expected reason."""
    if not (response or "").strip():
        return 0.0
    user_prompt = (
        f"Task instruction:\n{intent}\n\n"
        f"Reference reason the task is unachievable:\n{reference_reason}\n\n"
        f"Agent's response:\n{response}"
    )
    return _ask(_UNACHIEVABLE_SYSTEM_PROMPT, user_prompt)
