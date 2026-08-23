# Security

## Credentials committed on purpose

This repository and the published environment backups contain credentials. They
are committed deliberately and are safe:

| What | Where | Why it is here |
| --- | --- | --- |
| GitLab instance secrets | `configs/GitLab_v1{2,6}/v1*_data/gitlab-secrets.json` (in [skillshift-envs](https://github.com/SkillShift-Bench/skillshift-envs)) | GitLab refuses to restore a backup without the matching secrets file |
| `byteblaze` / `a_very_secure_password_123!` | task configs, docs | the WebArena demo account inside the GitLab image |
| Magento `admin` / `password123`, `admin1234` | task configs, docs | the demo admin inside the Magento images |

All of them belong to **disposable benchmark instances that run on your own
machine and are not reachable from the internet**. They grant access to nothing
else. Every endpoint defaults to `localhost`.

GitHub's secret scanning flags `gitlab-secrets.json`. That alert is expected and
is not a leak. Please do not open an issue for it.

**Do not** deploy these images on a public host, and **do not** reuse these
passwords anywhere.

## Real secrets

No live API key is committed. The model API is configured through environment
variables (`my_api_key`, `my_base_url`, `my_model`) and never written to disk by
the harness. `scripts/smoke_test.py` scans the tree for OpenAI-style keys and
personal paths on every CI run.

If you find a real credential in this repository, please report it privately
rather than opening a public issue — see the contact in the paper.

## Running the benchmark safely

- The task environments run arbitrary web content and the harness executes model
  output as Python inside the browser context. Run them in a container or a VM
  you are willing to discard, not on a machine with credentials you care about.
- `EXECUTION_SHIFT_*` injects modal blockers by intercepting page routes. It
  affects only the benchmark's own browser context.
