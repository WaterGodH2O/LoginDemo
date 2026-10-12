# 接口执行
#
# 职责：按接口用例发送 HTTP 请求，并比较状态码和响应正文。
# 输入：接口用例列表；api_base、timeout。
# 输出：每条用例的编号、实际状态码、响应正文、通过或失败。
#
# 本机账号服务 http://localhost:5000 ，超时默认 120 秒。
# 使用标准库发请求，不写 Playwright。
# 同一轮用例共用 Cookie，便于登录后请求 /api/me。

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar

from cases import ApiCase
from config import Config


@dataclass
class ApiResult:
    case_id: str
    requirement: str
    method: str
    url: str
    expected: str
    expected_status: int
    status: int
    body: str
    passed: bool
    actual: str


def run(api_cases: list[ApiCase], cfg: Config) -> list[ApiResult]:
    """按用例顺序请求。比较由本模块完成。"""
    if not api_cases:
        return []
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    results = []
    for case in api_cases:
        item = _one(case, cfg, opener)
        results.append(item)
        state = "通过" if item.passed else "失败"
        print(f"接口 {case.id} {state} HTTP {item.status}", flush=True)
    return results


def judge(status: int, body: str, expected_status: int, expected_text: str) -> bool:
    return status == expected_status and expected_text in body


def _one(case: ApiCase, cfg: Config, opener: urllib.request.OpenerDirector) -> ApiResult:
    url = _url(cfg.api_base, case.path)
    if url is None:
        actual = "地址不在账号服务上"
        return ApiResult(
            case.id, case.requirement, case.method, case.path, case.expected_text,
            case.expected_status, 0, "", False, actual,
        )
    status, body = _request(case.method, url, case.body, cfg.timeout, opener)
    passed = judge(status, body, case.expected_status, case.expected_text)
    snippet = body.replace("\n", " ")
    if len(snippet) > 200:
        snippet = snippet[:200]
    actual = f"HTTP {status}，正文「{snippet}」"
    return ApiResult(
        case.id,
        case.requirement,
        case.method,
        url,
        case.expected_text,
        case.expected_status,
        status,
        body,
        passed,
        actual,
    )


def _url(base: str, path: str) -> str | None:
    if path.startswith("http://") or path.startswith("https://"):
        if path.startswith(base.rstrip("/") + "/") or path == base.rstrip("/"):
            return path
        return None
    route = path if path.startswith("/") else "/" + path
    return base.rstrip("/") + route


def _request(method: str, url: str, body: object, timeout: int, opener: urllib.request.OpenerDirector) -> tuple[int, str]:
    data = None
    headers = {}
    if method.upper() not in {"GET", "HEAD"} and body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return int(response.status), raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), raw
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, f"无法连接：{exc}"
