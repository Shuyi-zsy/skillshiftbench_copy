import re
import time
import random
import logging
from typing import Optional
from urllib.parse import unquote
from playwright.sync_api import sync_playwright, Route, Request

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# --- 弹窗注入模式 (Addon 1 专用) ---
POPUP_MODE_ONCE = "once"          # 只在开头注入一次，关闭后不再出现 (默认，保持原行为)
POPUP_MODE_MULTIPLE = "multiple"  # 每次页面导航都重新注入
POPUP_MODE_RANDOM = "random"      # 随机时机注入 (按概率决定是否注入 + 页面内随机延迟弹出)

VALID_POPUP_MODES = frozenset(
    {POPUP_MODE_ONCE, POPUP_MODE_MULTIPLE, POPUP_MODE_RANDOM}
)

# random 模式默认参数
DEFAULT_RANDOM_PROBABILITY = 0.5     # 每次 document 加载有 50% 概率注入弹窗
DEFAULT_RANDOM_MAX_DELAY_MS = 5000   # 页面内最多延迟 5s 后弹出

# 弹窗 JS 模板。使用占位符注释按模式装配，避免与 CSS 花括号冲突。
#   /*__GUARD_OPEN__*/ .. /*__GUARD_CLOSE__*/  控制是否受持久化关闭标记约束
#   /*__PERSIST_CLOSE__*/                       关闭时是否写入 localStorage 持久标记
#   /*__SCHEDULE__*/                            立即弹出还是随机延迟弹出
OVERLAY_JS_TEMPLATE = """
<script>
document.addEventListener("DOMContentLoaded", function popupHandler() {
    function showPopup() {
        /*__GUARD_OPEN__*/
        // Create overlay
        var overlay = document.createElement("div");
        overlay.id = "my-overlay";
        overlay.style.position = "fixed";
        overlay.style.top = "0";
        overlay.style.left = "0";
        overlay.style.width = "100%";
        overlay.style.height = "100%";
        overlay.style.backgroundColor = "rgba(0, 0, 0, 0.8)";
        overlay.style.display = "flex";
        overlay.style.zIndex = "9999";
        overlay.style.pointerEvents = "auto";

        // Disable all interactions on the rest of the page
        document.body.style.pointerEvents = "none";  // Disable all pointer events on the body
        document.body.style.overflow = "hidden";  // Disable scrolling

        // Create popup
        var popup = document.createElement("div");
        popup.style.position = "relative";
        popup.style.backgroundColor = "white";
        popup.style.padding = "20px";
        popup.style.borderRadius = "10px";
        popup.style.boxShadow = "0 4px 8px rgba(0, 0, 0, 0.1)";
        popup.style.top = "700px"; // distance from the top
        popup.style.left = "600px"; // distance from the left
        popup.style.width = "400px"; // width of popup
        popup.style.height = "100px"; // height of popup

        popup.innerHTML = `
            <span id="close-popup" style="
                position: absolute;
                top: -20px;  /* Moves the close button higher */
                right: 5px;
                font-size: 24px;
                font-weight: bold;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: red;
                color: white;
                border-radius: 50%;
                cursor: pointer;
                user-select: none;
                box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.3);
            ">✖</span>

            <p style="margin-top: 30px;">This is a test popup!</p>
        `;

        // Append popup to overlay
        overlay.appendChild(popup);
        document.body.appendChild(overlay);

        // Close the popup when the X is clicked
        document.getElementById("close-popup").addEventListener("click", function() {
            document.body.removeChild(overlay);
            /*__PERSIST_CLOSE__*/
            document.body.style.pointerEvents = "auto";  // Re-enable pointer events after popup is closed
            document.body.style.overflow = "auto";  // Re-enable scrolling

            // Send a signal to the server to stop interception
            fetch("/popup-closed", { method: "POST" });

            // remove event listener when we remove pop-up so if we want to intercept again it can
            document.removeEventListener("DOMContentLoaded", popupHandler);

        });
        /*__GUARD_CLOSE__*/
    }

    /*__SCHEDULE__*/
});
</script>

"""


def build_overlay_js(
    mode: str = POPUP_MODE_ONCE,
    max_delay_ms: int = DEFAULT_RANDOM_MAX_DELAY_MS,
) -> str:
    """
    根据弹窗注入模式装配注入到页面的 JS。

    - once:     受 localStorage("popupClosed") 持久标记约束，关闭后不再弹出，立即弹出。
    - multiple: 无持久标记，每次页面加载都会弹出 (配合服务端每次导航重新注入)。
    - random:   无持久标记，页面加载后经随机延迟弹出 (配合服务端按概率注入)。
    """
    if mode not in VALID_POPUP_MODES:
        raise ValueError(
            f"Invalid popup mode: {mode!r}. Must be one of {sorted(VALID_POPUP_MODES)}."
        )

    if mode == POPUP_MODE_ONCE:
        guard_open = 'if (!localStorage.getItem("popupClosed")) {'
        guard_close = "}"
        persist_close = 'localStorage.setItem("popupClosed", "true");'
    else:
        # multiple / random: 不使用持久标记，允许重复弹出
        guard_open = "if (true) {"
        guard_close = "}"
        persist_close = ""

    if mode == POPUP_MODE_RANDOM:
        # 页面内随机延迟弹出
        delay = max(0, int(max_delay_ms))
        schedule = (
            f"setTimeout(showPopup, Math.floor(Math.random() * {delay}));"
        )
    else:
        schedule = "showPopup();"

    return (
        OVERLAY_JS_TEMPLATE
        .replace("/*__GUARD_OPEN__*/", guard_open)
        .replace("/*__GUARD_CLOSE__*/", guard_close)
        .replace("/*__PERSIST_CLOSE__*/", persist_close)
        .replace("/*__SCHEDULE__*/", schedule)
    )


class InterferenceController:
    def __init__(
        self,
        addon_mode=1,
        target_keys=None,
        popup_mode: str = POPUP_MODE_ONCE,
        random_probability: float = DEFAULT_RANDOM_PROBABILITY,
        random_max_delay_ms: int = DEFAULT_RANDOM_MAX_DELAY_MS,
        seed: Optional[int] = None,
    ):
        self.addon = addon_mode

        # 校验并保存弹窗注入模式 (仅 addon==1 生效)
        if popup_mode not in VALID_POPUP_MODES:
            raise ValueError(
                f"Invalid popup_mode: {popup_mode!r}. "
                f"Must be one of {sorted(VALID_POPUP_MODES)}."
            )
        self.popup_mode = popup_mode

        # random 模式参数
        self.random_probability = min(1.0, max(0.0, float(random_probability)))
        self.random_max_delay_ms = max(0, int(random_max_delay_ms))
        self._rng = random.Random(seed)

        # 预生成好当前模式对应的注入 JS，避免每次请求重复装配
        self._overlay_js = build_overlay_js(
            mode=self.popup_mode,
            max_delay_ms=self.random_max_delay_ms,
        )

        # 定义需要监听的目标环境 Key (域名:端口 或 域名)
        self.target_keys = target_keys if target_keys else [
            'localhost:8080', 'localhost:8000', 'localhost:8081', 'dockerized-magento.local', 'localhost:7780'
        ]

        # 状态管理：当前激活的环境
        self.active_env = None

        self.popup_closed_state = False

        # 预编译正则，用于检测开始和结束
        # 逻辑：http://{key}.*?logging=Starting(.*)
        self.start_patterns = {
            key: re.compile(rf'http://{key}.*\?logging=Starting(.*)') for key in self.target_keys
        }
        self.end_patterns = {
            key: re.compile(rf'http://{key}.*\?logging=Ending(.*)') for key in self.target_keys
        }

    def log(self, msg):
        print(f"[Controller] {msg}")

    def _should_inject_popup(self) -> bool:
        """
        根据弹窗注入模式判断本次 document 请求是否需要注入弹窗。
        仅在 addon==1 时调用。
        """
        if self.popup_mode == POPUP_MODE_ONCE:
            # 只注入一次：关闭后不再注入
            return not self.popup_closed_state

        if self.popup_mode == POPUP_MODE_MULTIPLE:
            # 每次页面导航都注入
            return True

        if self.popup_mode == POPUP_MODE_RANDOM:
            # 按概率决定本次是否注入
            return self._rng.random() < self.random_probability

        return False

    def route_handler(self, route: Route):
        request = route.request
        url = request.url

        # --- 1. 状态检查与切换逻辑 ---

        # 遍历所有 Key，检查是否触发了 开始 或 结束
        for key in self.target_keys:
            # 检查开始
            start_match = self.start_patterns[key].search(url)
            if start_match:
                decoded = unquote(start_match.group(1))
                self.log(f"🟢 Task START detected for {key}. Msg: {decoded}")
                self.active_env = key # 激活当前环境
                self.popup_closed_state = False
                # 继续请求，不拦截这个控制信号本身
                route.continue_()
                return

            # 检查结束
            end_match = self.end_patterns[key].search(url)
            if end_match:
                decoded = unquote(end_match.group(1))
                self.log(f"🔴 Task END detected for {key}. Msg: {decoded}")
                self.active_env = None # 关闭干扰
                self.popup_closed_state = False
                route.continue_()
                return

        # --- 2. 监听弹窗关闭信号 ---
        if "/popup-closed" in url and request.method == "POST":
            self.log("✅ Popup closed signal received.")
            # 这里可以根据需要添加逻辑，例如 "允许通过" 或 "关闭拦截"
            self.popup_closed_state = True
            # 返回 200 OK 也要加上 CORS 头，防止 JS 报错
            route.fulfill(
                status=200,
                body="OK",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Private-Network": "true"
                }
            )
            return

        # --- 3. 干扰注入逻辑 (仅当 active_env 有值时执行) ---

        if self.active_env:
            # 简单判断：只有当请求的 URL 包含当前激活的 Key 时才拦截 (防止误伤第三方资源)
            if self.active_env not in url:
                route.continue_()
                return

            self.log(f"⚡ Intercepting request in active env: {url}")

            # === Addon 2: 500 Error ===
            if self.addon == 2:
                self.log(">>> Injecting 500 Error")
                route.fulfill(
                    status=500,
                    content_type="text/html",
                    body="<html><body><h1>500 Server Error (Injected)</h1></body></html>"
                )
                return

            # === Addon 3: Network Delay ===
            if self.addon == 3:
                self.log(">>> Injecting 10s Delay")
                time.sleep(10)
                # 延迟后可以选择 abort (断网) 或者 continue (慢网)
                route.continue_()
                return

            # === Addon 1: Popup (修改响应体) ===
            if self.addon == 1:
                # 只有主文档 (HTML 页面) 需要注入弹窗脚本。其余资源
                # (css/js/字体/图片/xhr...) 直接放行，避免先 route.fetch() 取回
                # 响应、又落到末尾 route.continue_() 让浏览器再抓一次，
                # 导致每个资源被服务器抓取两遍、负载翻倍。
                if request.resource_type != "document":
                    route.continue_()
                    return

                # 根据弹窗注入模式决定本次是否注入
                if not self._should_inject_popup():
                    route.continue_()
                    return

                try:
                    response = route.fetch()
                    content_type = response.headers.get("content-type", "")
                    body = (
                        response.text()
                        if "text/html" in content_type
                        else None
                    )

                    # 注入 JS 到 </html> 之前
                    if body is not None and "</html>" in body:
                        self.log(
                            f">>> Injecting Popup JS into HTML "
                            f"(mode={self.popup_mode})"
                        )
                        new_body = body.replace(
                            "</html>", self._overlay_js + "</html>"
                        )
                        route.fulfill(response=response, body=new_body)
                    else:
                        # 已经抓取过一次，直接用原响应返回即可，
                        # 不要再 route.continue_() 触发二次抓取。
                        route.fulfill(response=response)
                except Exception as e:
                    self.log(f"Error fetching original response: {e}")
                    route.continue_()
                return

        # 如果没有激活，或者不符合干扰条件，直接放行
        route.continue_()
