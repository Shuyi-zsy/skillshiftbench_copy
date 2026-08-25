# Environments

Three websites, two versions each. Everything to deploy them lives in
[skillshift-envs](https://github.com/SkillShift-Bench/skillshift-envs); the
backups are on Hugging Face at
[`chenboyu/website_data`](https://huggingface.co/datasets/chenboyu/website_data).

| Site | v1 (source) | v2 (target) | Tasks |
| --- | --- | --- | --- |
| GitLab | 12.0.0 | 16.0.6 | 162 |
| Magento | 1.9 | 2.4 | 114 |
| WordPress | `news-portal` theme | `twentytwentyfour` theme | 79 |

## Host architecture

**SkillShift-Bench needs a `linux/amd64` host.** This is not a preference the
images could be rebuilt out of: three of the five environments are pinned to
upstream images that were never published for arm64.

| Environment | Upstream base | arm64 build |
| --- | --- | --- |
| GitLab 12 / 16 | `gitlab/gitlab-ce` | none |
| Magento 2.4 | WebArena's `shopping_admin_final_0719` | none |
| Magento 1.9 | `andreaskoch/dockerized-magento-php` | none |

Every image in `ghcr.io/skillshift-bench/*` is therefore `linux/amd64` only, and
`skillshift-envs` pins the platform explicitly rather than letting the builder
pick one that happens to match the build host.

On Apple Silicon these run only under Docker Desktop's emulation. That path is
not part of what SkillShift-Bench verifies -- the reported numbers come from
native amd64 hosts -- and GitLab, whose omnibus image supervises a dozen
services, has not been exercised under emulation at all. Treat a Mac as a place
to read the code, not to produce results.

## URL variables

The harness reads one variable per site and version:

```bash
export GITLAB_V1=http://localhost:8080
export GITLAB_V2=http://localhost:8081
export SHOPPING_ADMIN_V1=http://dockerized-magento.local/admin
export SHOPPING_ADMIN_V2=http://localhost:7780/admin
export WORDPRESS_V1=http://localhost:8000
export WORDPRESS_V2=http://localhost:8000
```

**These six are the only ones you set.** The `webarena` package underneath
browsergym asserts seven more at import time — `REDDIT`, `SHOPPING`,
`SHOPPING_ADMIN`, `GITLAB`, `WIKIPEDIA`, `MAP`, `HOMEPAGE` — and refuses to load
without them. The harness fills those in for the duration of a run from the six
above, and restores whatever you had afterwards; four of the seven name sites
this benchmark does not evaluate and are set to an obviously inert
`http://unused-by-skillshift.invalid`. You do not need to export them, and any
values you do export are ignored while a task is running.

**`WORDPRESS_V1` and `WORDPRESS_V2` pointing at the same URL is correct, not a
typo.** WordPress's contextual shift is a theme swap on a single instance, not a
second deployment. For the same reason WordPress ships one task file rather than
a v1/v2 pair. Only one context is live at a time:

```bash
skillshift-envs/scripts/wordpress_theme.sh --version v2   # switch to the target
skillshift-envs/scripts/wordpress_theme.sh --show         # which one is live
```

Check what is reachable:

```bash
skillshift env status
```

## Conditions and versions

`--condition` is the only supported way to select a cell. It sets the four
harness variables in one consistent step:

| Condition | `site_version` | perceptual | execution |
| --- | --- | --- | --- |
| `src` | v1 | off | off |
| `src-perc` | v1 | **on** | off |
| `src-exec` | v1 | off | **on** |
| `tgt` | v2 | off | off |
| `tgt-perc` | v2 | **on** | off |
| `tgt-exec` | v2 | off | **on** |

The paper defines no cell with both shifts active; asking for one is an error
rather than a silently accepted configuration.

## Bringing one up

```bash
cd skillshift-envs
./setup.sh --site gitlab --condition src      # pulls, starts, polls until ready
./setup.sh --site gitlab --condition src --dry-run   # or just print the plan
```

`--condition` is the primary spelling because it is what the paper and the rest
of the CLI use; `--version v1` / `--version v2` are accepted as synonyms, and
giving both is an error if they disagree. From a checkout of this repository
with `skillshift-envs` beside it, `skillshift env up --site gitlab --condition
src` runs the same script.

`setup.sh` also checks for host port collisions before starting anything, and
warns when a leftover Docker volume would mask the data in a freshly pulled
image.

**The pre-built images are not published yet.** Until they are, use `--from-hf`,
which downloads the backup and reconstructs the environment locally:

```bash
./setup.sh --site gitlab --condition src --from-hf
```

The Hugging Face backups:

| File | Environment |
| --- | --- |
| `1764075746_2025_11_25_12.0.0_gitlab_backup.tar` | GitLab 12.0 |
| `1764424641_2025_11_29_16.0.6_gitlab_backup.tar` | GitLab 16.0 |
| `magento-full-backup.tar.gz` | Magento 1.9 |
| `dist_package.zip` | WordPress (includes `drift_manager.sh`) |

**Magento 2.4 is not re-hosted.** It is WebArena's `shopping_admin_final_0719.tar`;
get it from the WebArena mirrors and follow their base-URL configuration.

Magento 1.9 needs a hosts entry:

```bash
echo "127.0.0.1 dockerized-magento.local" | sudo tee -a /etc/hosts
```

## Health and version checks

Being reachable and being *the right environment* are two different claims, and
both are checked. `skillshift env status` probes the URL and then defers to
`skillshift-envs/scripts/healthcheck.sh` for the version, so there is one set of
criteria rather than two that can drift:

| Environment | Ready when | Version read from |
| --- | --- | --- |
| GitLab 12 / 16 | the sign-in page answers **and** `gitlab-ctl status` shows nothing down | `/opt/gitlab/embedded/service/gitlab-rails/VERSION` |
| Magento 1.9 | `/admin` answers | `Mage::getVersionInfo()` |
| Magento 2.4 | `/admin` answers | `bin/magento --version` |
| WordPress | the site answers | `wp core version`, and the active theme |

A version mismatch is reported as `WRONG VERSION` and counts the environment as
not ready. Results from GitLab 15 are not results from this benchmark, and the
failure needs to be loud rather than buried in a footnote.

Without a `skillshift-envs` checkout the status line says
`version not checked` rather than claiming a version it has not verified.

## Ports

| Environment | Host ports |
| --- | --- |
| GitLab 12 | 8080, 8443, 2222 |
| GitLab 16 | 8081, 8444, 2223 |
| Magento 1.9 | 80, 443, 3307, 8083 (phpMyAdmin) |
| Magento 2.4 | 7780 |
| WordPress | 8000 |

Upstream's dockerized-magento publishes phpMyAdmin on 8080, which collides with
GitLab 12; `skillshift-envs` moves it to 8083 so both source-context sites can
run at once.

## Notes

- GitLab is slow to become ready on a cold start — minutes, not seconds.
  `skillshift env status` polls rather than guessing.
- The credentials in the configs are disposable and required for restore. See
  [../SECURITY.md](../SECURITY.md).
- Image digests are published in `skillshift-envs/DIGESTS.json` and recorded in
  every run receipt, so the leaderboard can tell whether a run used the official
  environment.
- `magento-v24` is the one entry in that file that is not a registry digest, and
  that is deliberate rather than an oversight. The environment is WebArena's
  `shopping_admin_final_0719`, linked rather than re-hosted, and it arrives as a
  tar you `docker load`. A loaded image has no `RepoDigest` -- that field is a
  registry's content address, and no registry ever served this image -- so the
  entry records the image's *config* digest instead. `docker load` copies that
  value verbatim out of the archive, so two people who load the same tar record
  the same digest. It cannot be used to pull anything.
