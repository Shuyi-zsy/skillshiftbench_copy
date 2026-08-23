import logging
import os
import re
import time

import playwright.sync_api
import requests

logger = logging.getLogger(__name__)

AVAILABLE_VERSIONS = ["v1", "v2"]

# 定义站点名称
SITE_NAMES = ("GITLAB", "SHOPPING_ADMIN", "WORDPRESS")


class MyBenchmarkInstance:
    """
    支持多版本网站的 Instance 管理器
    """

    def __init__(self) -> None:
        self.urls = {}
        self.credentials = {}

        for site in SITE_NAMES:
            self.urls[site.lower()] = {}

            for version in AVAILABLE_VERSIONS:
                env_var_name = f"{site}_{version.upper()}"

                assert env_var_name in os.environ, (
                    f"Environment variable {env_var_name} missing.\n"
                    f"Please set {env_var_name} to the URL of the {version} version of {site}."
                )

                self.urls[site.lower()][version] = os.environ[env_var_name]

        ACCOUNTS = {
            "gitlab": {
                "username": "byteblaze",
                "password": "a_very_secure_password_123!",
            },
            "shopping_admin": {
                "username": "admin",
                "password": {
                    "v1": "password123",
                    "v2": "admin1234",
                },
            },
        }

        self.credentials = ACCOUNTS

    def ui_login(
        self,
        site: str,
        version: str,
        page: playwright.sync_api.Page,
    ):
        """
        根据 site 和 version 登录到对应版本的网站
        """
        site = site.lower()

        if site not in self.urls or version not in self.urls[site]:
            raise ValueError(f"Unknown site {site} or version {version}")

        base_url = self.urls[site][version]

        # open a new page tab to perform the login
        login_page = page.context.new_page()

        match site:
            case "gitlab":
                username = self.credentials[site]["username"]
                password = self.credentials[site]["password"]

                login_page.goto(
                    f"{base_url}/users/sign_in",
                    timeout=60000,
                    wait_until="domcontentloaded",
                )

                user_field = login_page.get_by_label("Username or email")
                # Under parallel workers the server can be slow to render the
                # form; wait explicitly with a generous timeout instead of
                # relying on the (short) context default, which otherwise makes
                # login flaky and strands the agent on the sign-in page.
                user_field.wait_for(state="visible", timeout=60000)
                user_field.fill(username, timeout=60000)
                login_page.locator("#user_password").fill(password, timeout=60000)
                login_page.get_by_role("button", name="Sign in").click(timeout=60000)

                login_page.goto(f"{base_url}/?logging=StartingRun1")

            case "shopping_admin":
                username = self.credentials[site]["username"]
                password = self.credentials[site]["password"][version]

                login_page.goto(
                    f"{base_url}",
                    timeout=60000,
                    wait_until="domcontentloaded",
                )

                # Under parallel workers the admin login form can take several
                # seconds to render; wait explicitly with a generous timeout
                # instead of the short context default, otherwise fill() times
                # out and the agent starts on the login page unauthenticated.
                user_field = login_page.locator("#username")
                user_field.wait_for(state="visible", timeout=60000)
                user_field.fill(username, timeout=60000)
                login_page.locator("#login").fill(password, timeout=60000)

                button_m1 = login_page.get_by_role("button", name="Login")
                button_m2 = login_page.get_by_role("button", name="Sign in")

                button_m1.or_(button_m2).click(timeout=60000)

                # Ensure the auth round-trip commits (session cookie set) before
                # the login tab is closed.
                try:
                    login_page.wait_for_load_state(
                        "domcontentloaded", timeout=60000
                    )
                except Exception as e:
                    logger.warning(f"shopping_admin post-login wait failed: {e}")

                # login_page.goto(f"{base_url}/?logging=StartingRun1")

            case "wordpress":
                # 当前 WordPress 不需要登录
                pass

            case _:
                raise ValueError(f"Unsupported site: {site}")

        login_page.close()