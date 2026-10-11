# 页面执行
#
# 职责：用子进程运行页面脚本，并收集退出码和标准输出。
# 输入：通过检查的脚本；headed、timeout、web_base。
# 输出：每条用例的编号、退出码、标准输出、地址、截图路径。
#
# 本机在仓库根目录执行 python pipeline/work/ui/<脚本>.py。
# 退出码 0 表示出现预期文案，1 表示没有。通过与否只看退出码。
# headed 关闭时无头；--headed 时浏览器可见。单条超时默认 30 秒。
# 失败截图目录：pipeline/work/screenshots/。
# 有页面用例时，启动前后端之前先核对 playwright。
# 未安装则用当前 Python 执行：
#   python -m pip install playwright
#   python -m playwright install chromium
# 安装失败则退出，并打印命令输出。本模块不 import playwright。

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

from cases import UiCase
from config import Config, PipelineError


@dataclass
class UiResult:
    case_id: str
    requirement: str
    script: str
    expected: str
    exit_code: int
    stdout: str
    url: str
    screenshot: str
    passed: bool
    actual: str


def run(ui_cases: list[UiCase], cfg: Config) -> list[UiResult]:
    """按用例顺序执行。没有页面用例时什么也不做。"""
    if not ui_cases:
        return []
    prepare_playwright()
    cfg.screenshot_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for case in ui_cases:
        results.append(_one(case, cfg))
        state = "通过" if results[-1].passed else "失败"
        print(f"页面 {case.id} {state} 退出码 {results[-1].exit_code}", flush=True)
    return results


def _one(case: UiCase, cfg: Config) -> UiResult:
    script = cfg.repo_root / case.script
    shot = f"{cfg.work_dir}/screenshots/{case.id}.png"
    env = os.environ.copy()
    env["WEB_BASE"] = cfg.web_base
    env["HEADED"] = "1" if cfg.headed else "0"
    env["PIPELINE_TIMEOUT"] = str(cfg.timeout)
    env["PIPELINE_CASE_ID"] = case.id
    env["PIPELINE_EXPECTED"] = case.expected
    env["PIPELINE_SCREENSHOT"] = shot
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(cfg.repo_root),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=cfg.timeout,
            check=False,
        )
        output = _merge(proc.stdout, proc.stderr)
        code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        output = _merge(_as_text(exc.stdout), _as_text(exc.stderr)) + "\n超时"
        code = 1
    url = _field(output, "地址：")
    screenshot = _field(output, "截图：") or shot
    actual = _field(output, "实际：") or _short(output)
    return UiResult(
        case.id,
        case.requirement,
        case.script,
        case.expected,
        code,
        output,
        url,
        screenshot,
        code == 0,
        actual,
    )


_PLAYWRIGHT_READY = [False]


def prepare_playwright() -> None:
    """当前解释器已有 playwright 则返回。否则安装包和 chromium。"""
    if _playwright_imports():
        if not _PLAYWRIGHT_READY[0]:
            print("playwright 已安装", flush=True)
            _PLAYWRIGHT_READY[0] = True
        return
    print("正在安装 playwright", flush=True)
    installed = subprocess.run(
        [sys.executable, "-m", "pip", "install", "playwright"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if installed.returncode != 0:
        raise PipelineError("安装 playwright 失败\n" + _command_output(installed))
    print("正在安装 chromium", flush=True)
    browser = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if browser.returncode != 0:
        raise PipelineError("安装 chromium 失败\n" + _command_output(browser))
    if not _playwright_imports():
        raise PipelineError("安装 playwright 失败：安装结束后仍无法导入")
    _PLAYWRIGHT_READY[0] = True


def _playwright_imports() -> bool:
    probe = subprocess.run(
        [sys.executable, "-c", "import playwright"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    return probe.returncode == 0


def _command_output(proc: subprocess.CompletedProcess[str]) -> str:
    text = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part and part.strip())
    lines = text.splitlines()
    if len(lines) > 40:
        lines = lines[-40:]
    body = "\n".join(lines).strip()
    return body or f"退出码 {proc.returncode}"


def _merge(out: str | None, err: str | None) -> str:
    parts = [part.strip() for part in (out, err) if part and part.strip()]
    return "\n".join(parts)


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _field(text: str, label: str) -> str:
    for line in text.splitlines():
        if line.startswith(label):
            return line.split("：", 1)[-1].strip()
    return ""


def _short(text: str, limit: int = 200) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[:limit]
