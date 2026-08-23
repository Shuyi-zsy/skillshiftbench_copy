# Quickstart

## 1. Install

```bash
git clone https://github.com/SkillShift-Bench/skillshift-bench
cd skillshift-bench
pip install -e ".[run]"
python -m playwright install chromium
```

The bare `pip install -e .` gives you the aggregation and validation path with
no browser stack — enough to check a `results.json` before opening a pull
request, and enough for CI.

Verify the checkout without Docker, a GPU or an API key:

```bash
python scripts/smoke_test.py
```

## 2. Bring up one website

Full instructions are in [environments.md](environments.md). The short version
for GitLab 12.0 (the `src` context):

```bash
git clone https://github.com/SkillShift-Bench/skillshift-envs
cd skillshift-envs && ./setup.sh --site gitlab --version v1
export GITLAB_V1=http://localhost:8080
```

GitLab takes several minutes to become ready on a cold start. Check with:

```bash
skillshift env status
```

## 3. Configure the model

```bash
export my_api_key=...          # your key
export my_base_url=https://api.openai.com/v1
export my_model=gpt-5-mini-2025-08-07
```

## 4. Run one task

```bash
skillshift run --agent reference \
    --site gitlab --condition src \
    --tasks skillshift.gitlab.v1.0 \
    --out runs/first
```

`reference` is the built-in no-skill ReAct agent — the calibration anchor, not a
competitive method. To run your own, see [custom-agent.md](custom-agent.md).

## 5. Run a condition, then report

```bash
skillshift run --agent reference --site gitlab --condition tgt-exec --out runs/demo
skillshift report runs/demo --out submission/ --name "Reference ReAct" --model "$my_model"
skillshift validate submission/results.json
```

`report` writes three files. `results.json` and `run_receipt.json` are what you
submit; `per_task.jsonl` stays on your machine — see
[results-policy.md](results-policy.md).

## Task ids

Canonical: `skillshift.<site>.<v1|v2>.<index>`, for example
`skillshift.gitlab.v1.9`. The version-free form `skillshift.gitlab.9` names the
aligned task family and picks its version from `--condition`.

The artifact's `myBenchmark.<n>` ids still work but are deprecated: they are not
self-describing, because each site numbers its tasks from zero, so
`myBenchmark.9` means a different task on each site. Pass `--site` with them.
`data/tasks/id_map.csv` maps every id in both directions.
