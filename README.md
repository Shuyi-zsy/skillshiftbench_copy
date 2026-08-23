# SkillShift-Bench

**Do learned skills survive when the website changes?**

SkillShift-Bench evaluates learned-skill executability for web agents under
controlled same-site evolution. 355 tasks across GitLab, Magento and WordPress,
each run under six conditions that hold the task fixed and vary only the
conditions a reused skill depends on.

*EMNLP 2026 Main. Paper: (arXiv link pending). Leaderboard:
<https://skillshift-bench.github.io/leaderboard>*

```bash
pip install -e ".[run]"
skillshift env status
skillshift run --agent reference --site gitlab --condition tgt-exec --out runs/demo
```

---

## The three shifts

| | What evolves | What it stresses |
| --- | --- | --- |
| **Contextual** | version or theme of the same site | whether the skill is still *invoked* |
| **Perceptual** | layout, DOM, attributes, locators | whether it is still *grounded* |
| **Execution** | runtime modal blockers | whether it is still *feasible* |

Six conditions, matching the paper's Table 1: `src`, `src-perc`, `src-exec`,
`tgt`, `tgt-perc`, `tgt-exec`. `src` is the clean source context, `tgt` the
evolved target.

Task counts are fixed: **GitLab 162 + Magento 114 + WordPress 79 = 355**.

## What is published, and what is not

> SkillShift-Bench publishes the harness, the tasks, the environments, the
> reproduction commands and the aggregate results. It does **not** publish
> per-task pass/fail judgements or execution traces, so that the benchmark
> cannot be overfitted task by task and keeps its diagnostic value over time.

Aggregate entries stay accountable through a run receipt that commits to the
per-task results by hash without publishing them, aggregate-level consistency
checks, and a dispute clause. See [docs/results-policy.md](docs/results-policy.md).

The four compared methods (AWM, ASI, SkillWeaver, WALT) are not re-released
here; their leaderboard entries are transcribed from the paper and labelled
`reported-only`. See [docs/baselines.md](docs/baselines.md).

## Running your own method

Two methods. That is the whole interface.

```python
class MyAgent:
    def reset(self, task: TaskSpec, recorder: SkillRecorder) -> None: ...
    def act(self, obs: Observation) -> str: ...
```

Wrap each learned-skill invocation in `with recorder.call("my.skill"):` and the
harness computes Average Skill Calls and Skill Failure Rate for you.
[docs/custom-agent.md](docs/custom-agent.md) walks through it in fifteen minutes;
[examples/minimal_agent.py](examples/minimal_agent.py) is a complete agent in
fifty lines.

## Command line

```bash
skillshift env status                        # which sites and versions are reachable
skillshift run --agent <spec> --all          # 3 sites x 6 conditions
skillshift report runs/mine --out submission/ --name M --model gpt-5-mini-2025-08-07
skillshift validate submission/results.json  # exactly the leaderboard's checks
```

## Installation

```bash
pip install -e .              # aggregation and validation only: no browser stack
pip install -e ".[run]"       # + browsergym, playwright, an OpenAI-compatible client
pip install -e ".[run,mpcr]"  # + the optional embedding retrieval path
```

`requirements-lock.txt` is the exact environment the paper's experiments ran in,
kept for bit-exact reproduction.

Environments (Docker images, restore scripts, health checks) live in
[skillshift-envs](https://github.com/SkillShift-Bench/skillshift-envs); the
backups are on Hugging Face at
[`chenboyu/website_data`](https://huggingface.co/datasets/chenboyu/website_data).
See [docs/environments.md](docs/environments.md).

## Credentials in this repository — read this before filing an issue

`Data/configs/*/gitlab-secrets.json` and the demo accounts (`byteblaze`,
Magento `admin`) belong to **disposable local benchmark instances** and are
required to restore the published backups. They are not personal credentials and
grant access to nothing outside a container on your own machine. GitHub's secret
scanning will flag them; that is expected. See [SECURITY.md](SECURITY.md).

## Documentation

| | |
| --- | --- |
| [quickstart.md](docs/quickstart.md) | from clone to a first task |
| [environments.md](docs/environments.md) | deploying the three websites |
| [custom-agent.md](docs/custom-agent.md) | **running your own method** |
| [metrics.md](docs/metrics.md) | SR / AS / ASC / SFR, and how they aggregate |
| [results-policy.md](docs/results-policy.md) | what is published, and why |
| [baselines.md](docs/baselines.md) | the four compared methods |
| [submit.md](docs/submit.md) | getting onto the leaderboard |

## Citation

See [CITATION.cff](CITATION.cff).

## License

MIT for the code ([LICENSE](LICENSE)). The website environments are derived from
upstream projects under their own terms — see [DATA_LICENSE](DATA_LICENSE).
