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

**`WORDPRESS_V1` and `WORDPRESS_V2` pointing at the same URL is correct, not a
typo.** WordPress's contextual shift is a theme swap on a single instance
(`drift_manager.sh drift twentytwentyfour`), not a second deployment. For the
same reason WordPress ships one task file rather than a v1/v2 pair.

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

## Getting the images

Pre-built images with the data already baked in are the intended path, so that
nobody has to run a restore by hand:

```bash
cd skillshift-envs
./setup.sh --site gitlab --version v1     # pulls, starts, polls until ready
```

The Hugging Face backups remain available as a fallback (`./setup.sh --from-hf`):

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

## Notes

- GitLab is slow to become ready on a cold start — minutes, not seconds.
  `skillshift env status` polls rather than guessing.
- The credentials in the configs are disposable and required for restore. See
  [../SECURITY.md](../SECURITY.md).
- Image digests are published in `skillshift-envs/DIGESTS.json` and recorded in
  every run receipt, so the leaderboard can tell whether a run used the official
  environment.
