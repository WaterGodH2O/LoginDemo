# 模型调用
#
# 职责：按 Chat Completions 请求远程接口，返回回复正文。
# 输入：llm_base_url、llm_model、api_key，以及消息列表。
# 输出：回复字符串。失败时不写文件，打印 HTTP 状态码后由入口退出。
#
# 请求为 POST {llm_base_url}/chat/completions。请求体字段是 model 和 messages。
# messages 是数组，元素为 {role, content}。role 只用 system、user、assistant。
# system 只放规则；首轮 user 是打包后的源码和任务；之后 assistant 接模型回复，user 接执行结果。
# 这是各兼容接口通用的消息格式，不是 Claude/Gemini 官方原生格式。
#
# 本机默认地址 https://api.openai.com/v1 ，模型 gpt-4o-mini。
# 密钥只从环境变量 LLM_API_KEY 进入 Authorization 头。
# 单次请求超时使用 --timeout，默认 30 秒。

from __future__ import annotations

import json
import urllib.error
import urllib.request

from config import Config, PipelineError

SYSTEM_RULES = "\n".join(
    [
        "预期以 PRD 为准。",
        "源码缺少长度校验时不得把预期改成注册成功。",
        "不修改产品代码。",
    ]
)


def system_message() -> dict[str, str]:
    return {"role": "system", "content": SYSTEM_RULES}


def complete(cfg: Config, messages: list[dict[str, str]]) -> str:
    """发送 messages。密钥放在请求头，不进入正文，也不打印。"""
    url = cfg.llm_base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    payload = json.dumps(
        {"model": cfg.llm_model, "messages": messages},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    request.add_header("Authorization", f"Bearer {cfg.api_key}")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=cfg.timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        raise PipelineError(f"调用失败：HTTP {exc.code}") from None
    except urllib.error.URLError:
        raise PipelineError("调用失败：HTTP 无状态码") from None
    if status and status >= 400:
        raise PipelineError(f"调用失败：HTTP {status}")
    return _content(raw)


def _content(raw: str) -> str:
    try:
        payload = json.loads(raw)
        content = payload["choices"][0]["message"]["content"]
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
