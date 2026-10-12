# 模型调用
#
# 职责：按 Chat Completions 请求远程接口，返回回复正文。
# 输入：llm_base_url、llm_model、api_key，以及消息列表。
# 输出：回复字符串。失败时不写测试文档，打印 HTTP 状态码后由入口退出。
#
# 请求为 POST {llm_base_url}/chat/completions。请求体字段是 model、messages、max_tokens。
# max_tokens 默认 16384，即 gpt-4o-mini 的最大输出。模型自身上限无法取消。
# messages 是数组，元素为 {role, content}。role 只用 system、user、assistant。
# system 只放规则；首轮 user 是打包后的源码和任务；之后 assistant 接模型回复，user 接执行结果。
# 这是各兼容接口通用的消息格式，不是 Claude/Gemini 官方原生格式。
#
# 本机默认地址 https://api.openai.com/v1 ，模型 gpt-4o-mini。
# 密钥只从环境变量 LLM_API_KEY 进入 Authorization 头。
# 正式打包源码前，先发一条最短对话，确认密钥和模型可用，并在终端回显回复。
# 这次探测单独超时 20 秒，不使用 --timeout。
# 等待回复时在终端转圈。正式请求超时使用 --timeout，默认 120 秒。
# 超时不打 traceback，由入口退出。
# 探测的用户消息、之后每次用户消息和模型回复写入工作目录 dialogue.log。
# 每次运行先覆盖该文件。不写密钥、Authorization 头，也不写请求 URL。
# --verbose 只控制终端回显，不控制这份日志。

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request

from config import Config, PipelineError

PROBE_TIMEOUT = 20
PROBE_MESSAGE = "这是连通性测试。只回复两个字：正常"
DIALOGUE_NAME = "dialogue.log"

SYSTEM_RULES = "\n".join(
    [
        "预期以 PRD 为准。",
        "源码缺少长度校验时不得把预期改成注册成功。",
        "不修改产品代码。",
    ]
)


def system_message() -> dict[str, str]:
    return {"role": "system", "content": SYSTEM_RULES}


def reset_dialogue_log(cfg: Config) -> None:
    """创建工作目录，并覆盖本轮的对话日志。"""
    path = _dialogue_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n"):
        pass


def write_dialogue(cfg: Config, title: str, text: str) -> None:
    """追加一段原文。只写标题和正文，不写密钥、请求头和请求 URL。"""
    path = _dialogue_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _hide_key(cfg, text or "")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"======== {title} ========\n")
        handle.write(body)
        if not body.endswith("\n"):
            handle.write("\n")
        handle.write("\n")


def probe(cfg: Config) -> None:
    """发送一条最短对话。有正文才算连通，并在终端回显回复摘要。"""
    print(f"正在确认模型：{cfg.llm_model}", flush=True)
    write_dialogue(cfg, "发给模型：连通性探测", PROBE_MESSAGE)
    reply = complete(
        cfg,
        [{"role": "user", "content": PROBE_MESSAGE}],
        timeout=PROBE_TIMEOUT,
    )
    write_dialogue(cfg, "模型回复", reply)
    text = " ".join(reply.split())
    if len(text) > 40:
        text = text[:40] + "…"
    print(f"模型可用：{cfg.llm_model} 回复「{text}」", flush=True)


def complete(cfg: Config, messages: list[dict[str, str]], timeout: int | None = None) -> str:
    """发送 messages。密钥放在请求头，不进入正文，也不打印，不写入对话日志。timeout 为空时用 --timeout。"""
    limit = cfg.timeout if timeout is None else timeout
    url = cfg.llm_base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    payload = json.dumps(
        {"model": cfg.llm_model, "messages": messages, "max_tokens": cfg.max_tokens},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    request.add_header("Authorization", f"Bearer {cfg.api_key}")
    request.add_header("Content-Type", "application/json")
    try:
        with _spinner():
            with urllib.request.urlopen(request, timeout=limit) as response:
                raw = response.read().decode("utf-8", errors="replace")
                status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        raise PipelineError(f"调用失败：HTTP {exc.code}") from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise PipelineError(f"调用失败：{limit} 秒内无响应") from None
        raise PipelineError("调用失败：HTTP 无状态码") from None
    except TimeoutError:
        raise PipelineError(f"调用失败：{limit} 秒内无响应") from None
    if status and status >= 400:
        raise PipelineError(f"调用失败：HTTP {status}")
    return _content(raw)


class _spinner:
    """等待期间在同一行转圈。输出被重定向时不显示。"""

    _FRAMES = "|/-\\"
    _LABEL = "正在等待模型回复"

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "_spinner":
        if not sys.stdout.isatty():
            return self
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> bool:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
            print("\r" + " " * 32 + "\r", end="", flush=True)
        return False

    def _run(self) -> None:
        index = 0
        while not self._stop.wait(0.12):
            frame = self._FRAMES[index % len(self._FRAMES)]
            print(f"\r{frame} {self._LABEL}", end="", flush=True)
            index += 1


def _dialogue_path(cfg: Config):
    return cfg.work_path / DIALOGUE_NAME


def _hide_key(cfg: Config, text: str) -> str:
    key = cfg.api_key
    if not key or key not in text:
        return text
    return text.replace(key, "***")


def _content(raw: str) -> str:
    try:
        payload = json.loads(raw)
        choice = payload["choices"][0]
        content = choice["message"]["content"]
        finish = choice.get("finish_reason")
        if finish and finish != "stop":
            print(f"模型结束原因：{finish}", flush=True)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise PipelineError("调用失败：HTTP 200 但无正文") from exc
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        content = "".join(parts)
    if not isinstance(content, str) or not content.strip():
        raise PipelineError("调用失败：HTTP 200 但无正文")
    return content
