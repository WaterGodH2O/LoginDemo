# 服务启动
#
# 职责：先核对环境，再保证前端页面和账号服务可访问。
# 端口已有进程监听则复用并记录 pid，不重复启动。结束时不关闭这些进程。
# 输入：web_base、api_base。
# 输出：前端基址、后端基址，以及本次新启动进程的 pid。
#
# 本机（Windows，仓库根目录 B:\cs\Internship）：
#   后端：python backend/app.py
#         工作目录是仓库根目录。监听 5000，地址 http://localhost:5000。
#         健康检查 GET /api/health。依赖见 backend/requirements.txt。
#   前端：本机 PATH 中要有 node 和 npm。
#         在 frontend/ 执行 npm install
#         （装上 React、React DOM、React Router、Ant Design、Axios、Vite）。
#         再在仓库根目录执行 npm run dev --prefix frontend，脚本是 vite。
#         监听 5173，地址 http://localhost:5173。页面 /register、/login、/home。
#   5000 或 5173 已监听则复用，不再启动对应进程。
#
# 真正启动之前核对，缺了就打印并退出：
#   当前 Python 能导入 backend/requirements.txt 里的包（flask、flask-cors 等）。
#   缺失时提示在仓库根目录执行 pip install -r backend/requirements.txt。
#   node 与 npm 都能在 PATH 中找到。缺失时说明需要 Node.js 和 npm。
# 有页面用例时，另由页面执行模块核对 playwright，未安装再装浏览器。
# 完成条件：GET /api/health 成功，且 /register 能打开。
# 单次探测使用 --timeout，默认 120 秒。

from __future__ import annotations

import locale
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from config import Config, PipelineError


@dataclass
class ServerInfo:
    web_base: str
    api_base: str
    started_pids: list[int] = field(default_factory=list)
    reused_pids: list[int] = field(default_factory=list)
    # 保住日志句柄，避免子进程的标准输出被提前关掉。
    logs: list = field(default_factory=list)


_RUNTIME_OK = False


def check_runtime(cfg: Config) -> None:
    """启动前后端之前核对当前 Python 依赖，以及 PATH 里的 node、npm。"""
    global _RUNTIME_OK
    if _RUNTIME_OK:
        return
    problems: list[str] = []
    missing = _missing_backend_deps(cfg)
    if missing:
        names = "、".join(missing)
        problems.append(
            f"缺少后端依赖：{names}。请在仓库根目录执行 pip install -r backend/requirements.txt"
        )
    node = _which_tool("node")
    npm = _which_tool("npm")
    if not node and not npm:
        problems.append("未找到 node 和 npm。启动前端需要本机的 Node.js 和 npm")
    elif not node:
        problems.append("未找到 node。启动前端需要本机的 Node.js 和 npm")
    elif not npm:
        problems.append("未找到 npm。启动前端需要本机的 Node.js 和 npm")
    else:
        problems.extend(_tool_runs(node, "node"))
        problems.extend(_tool_runs(npm, "npm"))
    if problems:
        raise PipelineError("\n".join(problems))
    _RUNTIME_OK = True
    print("环境核对通过：后端依赖、node、npm", flush=True)


def ensure(cfg: Config) -> ServerInfo:
    """需要跑页面或接口时调用。先核对环境，端口占用则复用。"""
    check_runtime(cfg)
    info = ServerInfo(cfg.web_base, cfg.api_base)
    logs = cfg.work_path / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    api_port = _port(cfg.api_base)
    web_port = _port(cfg.web_base)
    _ensure_backend(cfg, info, api_port, logs / "backend.log")
    _ensure_frontend(cfg, info, web_port, logs / "frontend.log")

    health = cfg.api_base + "/api/health"
    page = cfg.web_base + "/register"
    if _status(health, cfg.timeout) != 200:
        raise PipelineError(f"账号服务未就绪：{health}")
    page_status = _status(page, cfg.timeout)
    if page_status < 200 or page_status >= 400:
        raise PipelineError(f"注册页未打开：{page}")

    started = "、".join(str(pid) for pid in info.started_pids) or "无"
    reused = "、".join(str(pid) for pid in info.reused_pids) or "无"
    print(f"前端基址：{info.web_base}", flush=True)
    print(f"后端基址：{info.api_base}", flush=True)
    print(f"新启动 pid：{started}", flush=True)
    print(f"复用 pid：{reused}", flush=True)
    return info


def parse_netstat(text: str, port: int) -> int | None:
    """从 netstat 文本里取正在监听该端口的 pid。"""
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        state = parts[3].upper()
        if state not in {"LISTENING", "侦听"}:
            continue
        if _addr_port(parts[1]) != port:
            continue
        if parts[4].isdigit():
            return int(parts[4])
    return None


def _ensure_backend(cfg: Config, info: ServerInfo, port: int, log_path: Path) -> None:
    occupied, pid = _occupied(cfg.api_base, port)
    if occupied:
        _remember_reuse(info, "后端", port, pid)
        return
    app = cfg.repo_root / "backend" / "app.py"
    if not app.is_file():
        raise PipelineError("缺少 backend/app.py")
    log = _open_log(log_path)
    info.logs.append(log)
    proc = subprocess.Popen(
        [sys.executable, "backend/app.py"],
        cwd=str(cfg.repo_root),
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=_flags(),
        env=_child_env(),
    )
    info.started_pids.append(proc.pid)
    print(f"后端已启动 pid {proc.pid}", flush=True)
    _wait(cfg, "后端", proc, log_path, lambda: _status(cfg.api_base + "/api/health", 3) == 200)


def _ensure_frontend(cfg: Config, info: ServerInfo, port: int, log_path: Path) -> None:
    occupied, pid = _occupied(cfg.web_base, port)
    if occupied:
        _remember_reuse(info, "前端", port, pid)
        return
    frontend = cfg.repo_root / "frontend"
    if not frontend.is_dir():
        raise PipelineError("缺少前端目录 frontend")
    npm = _npm()
    install_log = _open_log(log_path)
    info.logs.append(install_log)
    print("正在安装前端依赖", flush=True)
    installed = subprocess.run(
        [npm, "install"],
        cwd=str(frontend),
        stdout=install_log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=_flags(),
        check=False,
    )
    if installed.returncode != 0:
        raise PipelineError(f"npm install 失败\n{_tail(log_path)}")
    log = _open_log(log_path)
    info.logs.append(log)
    proc = subprocess.Popen(
        [npm, "run", "dev", "--prefix", "frontend"],
        cwd=str(cfg.repo_root),
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=_flags(),
        env=_child_env(),
    )
    info.started_pids.append(proc.pid)
    print(f"前端已启动 pid {proc.pid}", flush=True)
    page = cfg.web_base + "/register"
    _wait(cfg, "前端", proc, log_path, lambda: 200 <= _status(page, 3) < 400)


def _remember_reuse(info: ServerInfo, name: str, port: int, pid: int | None) -> None:
    if pid:
        info.reused_pids.append(pid)
        print(f"{name}端口 {port} 已监听，复用 pid {pid}", flush=True)
    else:
        print(f"{name}端口 {port} 已监听，未能解析 pid，仍复用", flush=True)


def _occupied(base: str, port: int) -> tuple[bool, int | None]:
    host = urlparse(base).hostname or "127.0.0.1"
    pid = _listening_pid(port)
    if pid:
        return True, pid
    if _accepts(host, port):
        return True, None
    return False, None


def _listening_pid(port: int) -> int | None:
    try:
        proc = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            creationflags=_flags(),
            check=False,
        )
    except OSError:
        return None
    return parse_netstat(proc.stdout or "", port)


def _accepts(host: str, port: int) -> bool:
    # localhost 在 Windows 上可能只通 127.0.0.1 或只通 ::1，两边都试。
    hosts = [host]
    if host == "localhost":
        hosts.extend(["127.0.0.1", "::1"])
    elif host == "127.0.0.1":
        hosts.append("localhost")
    for item in hosts:
        try:
            with socket.create_connection((item, port), timeout=1):
                return True
        except OSError:
            continue
    return False


def _missing_backend_deps(cfg: Config) -> list[str]:
    path = cfg.repo_root / "backend" / "requirements.txt"
    if not path.is_file():
        raise PipelineError("缺少 backend/requirements.txt")
    missing: list[str] = []
    for name, module in _requirement_modules(path):
        proc = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            missing.append(name)
    return missing


def _requirement_modules(path: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        name = re.split(r"[<>=!~;\[]", line, maxsplit=1)[0].strip()
        if not name:
            continue
        found.append((name, name.replace("-", "_")))
    return found


def _which_tool(name: str) -> str | None:
    if os.name == "nt" and name == "npm":
        return shutil.which("npm.cmd") or shutil.which("npm")
    return shutil.which(name)


def _tool_runs(path: str, label: str) -> list[str]:
    try:
        proc = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
            creationflags=_flags(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"无法执行 {label}：{exc}"]
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return [f"无法执行 {label}：{detail or proc.returncode}"]
    return []


def _wait(cfg: Config, label: str, proc: subprocess.Popen, log_path: Path, ready) -> None:
    deadline = time.time() + cfg.timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise PipelineError(f"{label}进程已退出，代码 {proc.returncode}\n{_tail(log_path)}")
        if ready():
            return
        time.sleep(0.4)
    raise PipelineError(f"{label}在 {cfg.timeout} 秒内未就绪\n{_tail(log_path)}")


def _status(url: str, timeout: float) -> int:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            response.read()
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0


def _port(url: str) -> int:
    parsed = urlparse(url)
    if parsed.port:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def _addr_port(address: str) -> int | None:
    if address.startswith("[") and "]" in address:
        rest = address.rsplit("]", 1)[-1]
        if rest.startswith(":") and rest[1:].isdigit():
            return int(rest[1:])
        return None
    if ":" in address:
        maybe = address.rsplit(":", 1)[-1]
        if maybe.isdigit():
            return int(maybe)
    return None


def _npm() -> str:
    name = "npm.cmd" if os.name == "nt" else "npm"
    found = shutil.which(name) or shutil.which("npm")
    if not found:
        raise PipelineError("未找到 npm。启动前端需要本机的 Node.js 和 npm")
    return found


def _flags() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _open_log(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    # 二进制追加，子进程直接写句柄。
    return path.open("ab")


def _tail(path: Path, limit: int = 40) -> str:
    if not path.is_file():
        return ""
    text = path.read_bytes().decode("utf-8", errors="replace")
    return "\n".join(text.splitlines()[-limit:])
