import json
import logging
import tempfile
import urllib.parse
import os
from typing import Optional, Tuple

import playwright.sync_api
from browsergym.core.task import AbstractBrowserTask

from .. import sites

from .. import registry as task_registry
from ..shifts.execution_shift import (
    DEFAULT_RANDOM_MAX_DELAY_MS,
    DEFAULT_RANDOM_PROBABILITY,
    POPUP_MODE_ONCE,
    VALID_POPUP_MODES,
    InterferenceController,
)
from ..shifts.perceptual_shift import DriftInjector
from .instance import MyBenchmarkInstance

logger = logging.getLogger(__name__)


# Derived from `skillshift.sites` so that the harness, the registry and the CLI
# cannot drift apart on what "admin" means.
SITE_KEY_MAP = {site.harness_key: site.instance_key for site in sites.all_sites()}

#: Placeholder each task file uses for its site's base URL.
PLACEHOLDER_MAP = {site.harness_key: f"__{site.env_prefix}__" for site in sites.all_sites()}


def get_str_env(*names: str, default: Optional[str] = None) -> Optional[str]:
    """
    依次读取多个环境变量名，返回第一个非空值。
    用于兼容 WEBSITE / website, SITE_VERSION / site_version。
    """
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip() != "":
            return value.strip()
    return default


def get_bool_env(*names: str, default: bool = False) -> bool:
    """
    从环境变量中读取布尔值。

    支持:
        true:  1, true, yes, y, on
        false: 0, false, no, n, off
    """
    true_values = {"1", "true", "yes", "y", "on"}
    false_values = {"0", "false", "no", "n", "off"}

    for name in names:
        value = os.environ.get(name)
        if value is None:
            continue

        value = value.strip().lower()

        if value in true_values:
            return True
        if value in false_values:
            return False

        raise ValueError(
            f"Invalid boolean value for environment variable {name}: {value}. "
            f"Expected one of {sorted(true_values | false_values)}."
        )

    return default


def get_task_file_path(website: str, site_version: str) -> str:
    """Locate the task JSON for one (website, version) pair.

    Task files live in `data/tasks/` and are addressed through the registry, so
    that the harness and the registry can never disagree about which file backs
    a given cell.
    """
    if website is None:
        raise ValueError(
            "Environment variable WEBSITE is not set. "
            "Expected one of: gitlab, admin, wordpress."
        )

    site = sites.get(website)
    path = task_registry.task_file_path(site.name, site_version)

    if not path.is_file():
        raise FileNotFoundError(
            f"Task config file not found: {path}. "
            f"Rebuild it with scripts/build_task_data.py."
        )

    return str(path)


def get_site_info(
    webarena_instance: MyBenchmarkInstance,
    website: str,
    site_version: str,
) -> tuple[str, str, str]:
    """
    根据 website 和 site_version 返回:
        site_key: webarena_instance.urls 里的 key
        site_placeholder: 任务 JSON 中的 placeholder
        site_url: 当前网站当前版本的 URL
    """
    site = sites.get(website)
    site_key = site.instance_key
    site_placeholder = f"__{site.env_prefix}__"

    if site_key not in webarena_instance.urls:
        raise ValueError(
            f"Site key {site_key} not found in webarena_instance.urls. "
            f"Available keys: {list(webarena_instance.urls.keys())}."
        )

    if site_version not in webarena_instance.urls[site_key]:
        raise ValueError(
            f"Version {site_version} not found for site {site_key}. "
            f"Available versions: {list(webarena_instance.urls[site_key].keys())}."
        )

    site_url = webarena_instance.urls[site_key][site_version]

    return site_key, site_placeholder, site_url


def add_query_param(url: str, key: str, value: str) -> str:
    """
    给 URL 安全地添加 query 参数。
    避免手写 f"{url}/?..."
    """
    parts = urllib.parse.urlsplit(url)
    query_items = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query_items.append((key, value))

    new_query = urllib.parse.urlencode(query_items)

    path = parts.path
    if path == "":
        path = "/"

    return urllib.parse.urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            path,
            new_query,
            parts.fragment,
        )
    )


class GenericMyBenchmarkTask(AbstractBrowserTask):
    """
    Base class for all MyBenchmark tasks.
    """

    def __init__(
        self,
        seed: int,
        task_id: Optional[int] = None,
        intent_template_id: Optional[int] = None,
        website: Optional[str] = None,
        site_version: Optional[str] = None,
        with_na_hint: bool = False,
        with_homepage_hint: bool = False,
    ) -> None:
        super().__init__(seed)

        # task properties, will be used to set up the browsergym environment
        self.viewport = {"width": 1280, "height": 720}
        self.slow_mo = 1000  # ms
        self.timeout = 10000  # ms

        # A canonical gym id (`skillshift.gitlab.v1.9`) carries its own site and
        # version, so it does not depend on the ambient environment.  The legacy
        # `myBenchmark.<n>` ids do not, and still read the environment.
        self.website = website or get_str_env("WEBSITE", "website")
        self.site_version = site_version or get_str_env(
            "SITE_VERSION",
            "site_version",
            default="v1",
        )

        if self.website is not None:
            self.website = sites.get(self.website).harness_key

        if self.site_version is not None:
            self.site_version = self.site_version.lower()

        self.webarena_instance = MyBenchmarkInstance()

        self.site_key, self.site_placeholder, self.site_url = get_site_info(
            webarena_instance=self.webarena_instance,
            website=self.website,
            site_version=self.site_version,
        )

        self.config_file: Optional[str] = None
        self.with_na_hint = with_na_hint
        self.with_homepage_hint = with_homepage_hint

        self.with_perceptual_shift = get_bool_env(
            "WITH_PERCEPTUAL_SHIFT",
            "with_perceptual_shift",
            default=False,
        )
        self.with_execution_shift = get_bool_env(
            "WITH_EXECUTION_SHIFT",
            "with_execution_shift",
            default=False,
        )

        # 弹窗注入模式: once (默认) / multiple / random
        popup_mode = (
            get_str_env(
                "EXECUTION_SHIFT_POPUP_MODE",
                "execution_shift_popup_mode",
                default=POPUP_MODE_ONCE,
            )
            or POPUP_MODE_ONCE
        ).strip().lower()
        if popup_mode not in VALID_POPUP_MODES:
            raise ValueError(
                f"Invalid EXECUTION_SHIFT_POPUP_MODE={popup_mode!r}. "
                f"Must be one of {sorted(VALID_POPUP_MODES)}."
            )
        self.execution_shift_popup_mode = popup_mode

        # random 模式参数
        probability_str = get_str_env(
            "EXECUTION_SHIFT_RANDOM_PROBABILITY",
            "execution_shift_random_probability",
        )
        self.execution_shift_random_probability = (
            float(probability_str)
            if probability_str is not None
            else DEFAULT_RANDOM_PROBABILITY
        )

        delay_str = get_str_env(
            "EXECUTION_SHIFT_RANDOM_MAX_DELAY_MS",
            "execution_shift_random_max_delay_ms",
        )
        self.execution_shift_random_max_delay_ms = (
            int(delay_str)
            if delay_str is not None
            else DEFAULT_RANDOM_MAX_DELAY_MS
        )

        # one and only one of task id and template id must be provided
        if (task_id is None) == (intent_template_id is None):
            raise ValueError(
                f"One and only one of 'task_id' and 'intent_template_id' "
                f"must be provided "
                f"(task_id={task_id}, intent_template_id={intent_template_id})."
            )

        json_file_path = get_task_file_path(
            website=self.website,
            site_version=self.site_version,
        )

        print(f"WEBSITE={self.website}")
        print(f"SITE_VERSION={self.site_version}")
        print(f"Loading task file: {json_file_path}")
        print(f"Using site URL: {self.site_url}")

        with open(json_file_path, "r", encoding="utf-8") as f:
            all_configs_str = f.read()

        # 根据当前 website 自动替换对应 placeholder
        replacements = {
            self.site_placeholder: self.site_url,
        }

        for pattern, target_url in replacements.items():
            all_configs_str = all_configs_str.replace(pattern, target_url)

        # 防止任务文件中仍残留未替换的 placeholder
        unresolved_placeholders = [
            placeholder
            for placeholder in PLACEHOLDER_MAP.values()
            if placeholder in all_configs_str
        ]

        if unresolved_placeholders:
            raise ValueError(
                f"Unresolved placeholders found in task config: "
                f"{unresolved_placeholders}. "
                f"Current WEBSITE={self.website}, SITE_VERSION={self.site_version}."
            )

        # load all task configs to JSON
        all_configs = json.loads(all_configs_str)

        # keep only the desired task configs
        if intent_template_id is not None:
            task_configs = [
                conf
                for conf in all_configs
                if conf["intent_template_id"] == intent_template_id
            ]

            if not task_configs:
                raise ValueError(
                    f"Could not find any task config with "
                    f"intent_template_id={intent_template_id}."
                )

        elif task_id is not None:
            task_configs = [
                conf
                for conf in all_configs
                if conf["task_id"] == task_id
            ]

            if not task_configs:
                raise ValueError(
                    f"Could not find any task config with task_id={task_id}."
                )

        self.task_configs = task_configs

    def setup(self, page: playwright.sync_api.Page) -> tuple[str, dict]:
        from .evaluators import evaluator_router

        if self.with_execution_shift:
            controller = InterferenceController(
                addon_mode=1,
                popup_mode=self.execution_shift_popup_mode,
                random_probability=self.execution_shift_random_probability,
                random_max_delay_ms=self.execution_shift_random_max_delay_ms,
            )

            # 挂载干扰逻辑
            page.route("**/*", controller.route_handler)

            logging_url = add_query_param(
                self.site_url,
                "logging",
                "StartingRun1",
            )

            page.goto(logging_url, timeout=60000)

        # pick a task at random
        self.config = self.random.choice(self.task_configs)

        # hack: dynamically build a config file to read from
        with tempfile.NamedTemporaryFile(
            mode="w+",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump(self.config, f)
            f.flush()
            self.config_file = f.name

        # build the evaluator
        self.evaluator = evaluator_router(self.config_file)

        # authenticate
        for site in self.config["sites"]:
            self.webarena_instance.ui_login(
                site=site,
                version=self.site_version,
                page=page,
            )

        # Inject the perceptual-shift drift AFTER authentication.
        # add_init_script is context-wide, so registering it earlier would also
        # run the drift on the hidden login tab opened by ui_login. The
        # structural (tag-replacement) mutation destroys/recreates the Magento
        # login form elements via replaceChild, which breaks form submission and
        # leaves the agent stranded on the login page. Authenticating first on a
        # clean context, then registering the script, still drifts every task
        # page the agent navigates to afterwards.
        if self.with_perceptual_shift:
            injector = DriftInjector()
            drift_script = injector.generate_drift_script(
                drift_type="all",
                intensity="high",
            )

            page.context.add_init_script(drift_script)

            try:
                client = page.context.new_cdp_session(page)
                client.send("Page.setBypassCSP", {"enabled": True})
            except Exception as e:
                logger.warning(f"Failed to enable CSP bypass via CDP: {e}")

        # set geolocation
        page.context.set_geolocation(self.config["geolocation"])

        # navigate to the starting url(s)
        if self.config["start_url"]:
            start_urls = self.config["start_url"].split(" |AND| ")

            for i, url in enumerate(start_urls):
                page.goto(
                    url,
                    timeout=60000,
                    wait_until="domcontentloaded",
                )

                if i < len(start_urls) - 1:
                    page = page.context.new_page()

        # recover goal
        goal = self.config["intent"]

        # This note is present in all webarena's agent prompts
        if self.with_homepage_hint:
            goal += f"""

(Note: if you want to visit other websites, check out the homepage at {self.webarena_instance.home_url}. It has a list of websites you can visit. {self.webarena_instance.home_url}/password.html lists all the account name and password for the websites. You can use them to log in to the websites.)
"""

        # This note is present in some of webarena's agent prompts
        if self.with_na_hint:
            goal += """\

If you believe the task is impossible to complete, provide the answer "N/A".
"""

        return goal, {
            "website": self.website,
            "site_version": self.site_version,
            "site_key": self.site_key,
            "site_url": self.site_url,
            "with_perceptual_shift": self.with_perceptual_shift,
            "with_execution_shift": self.with_execution_shift,
        }

    def cheat(
        self,
        page: playwright.sync_api.Page,
        chat_messages: list[str],
    ) -> None:
        raise NotImplementedError

    @classmethod
    def get_task_id(cls):
        """
        Generic class for several task ids, this way of obtaining the task id
        is not compatible for now.
        """
        raise NotImplementedError

    def teardown(self) -> None:
        # Nothing to be done here
        pass

    def validate(
        self,
        page: playwright.sync_api.Page,
        chat_messages: list[str],
    ) -> Tuple[float, bool, str, dict]:

        # safeguard: check that all open tabs are either blank or within
        # the list of WebArena URLs

        all_site_urls = []

        for versions in self.webarena_instance.urls.values():
            if isinstance(versions, dict):
                all_site_urls.extend(versions.values())
            else:
                all_site_urls.append(versions)


        authorized_locations = ["newtab", ""] + [
            urllib.parse.urlparse(url).netloc
            for url in all_site_urls
        ]

        authorized_locations = list(set(authorized_locations))

        for open_page in page.context.pages:
            page_location = urllib.parse.urlparse(open_page.url).netloc

            if page_location not in authorized_locations:
                return 0, True, "", {
                    "error": "Unauthorized url, terminating task",
                    "url": open_page.url,
                }

        # import webarena dynamically
        from webarena.browser_env.actions import ActionTypes

        # if any, use the last assistant message as the stop answer for webarena
        if chat_messages and chat_messages[-1]["role"] == "assistant":
            last_action = {
                "action_type": ActionTypes.STOP,
                "answer": chat_messages[-1]["message"],
            }
        elif chat_messages and chat_messages[-1]["role"] == "infeasible":
            last_action = {
                "action_type": ActionTypes.STOP,
                "answer": "N/A",
            }
        else:
            last_action = {
                "action_type": ActionTypes.NONE,
                "answer": "whatever",
            }

        # hack: fake trajectory for evaluation
        # only last_action["answer"] is used in the webarena evaluation codebase
        trajectory = [{}, last_action]  # StateInfo, Action

        # call the evaluator
        try:
            score = self.evaluator(
                trajectory=trajectory,
                config_file=self.config_file,
                page=page,
                client=None,
            )
        except AssertionError:
            logger.debug(
                "llm_fuzzy_match() bugfix applied: "
                "AssertionError in evaluator, using score = 0.0"
            )
            score = 0.0

        if score > 0 or last_action["action_type"] == ActionTypes.STOP:
            return score, True, "", {}

        return score, False, "", {}