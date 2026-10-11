# 文件收集
#
# 职责：按配置列出要送进首轮消息的文件，并读出原文。
# 输入：sources、prd、docs。
# 输出：文件列表。每项含相对仓库根目录的路径和原文。
#
# 本机默认读 frontend、backend，以及 docs/prd/登录注册Demo-PRD.md。
# 跳过 node_modules/、dist/、package-lock.json、__pycache__/、*.db、.git/、pipeline/work/。
# 依赖目录 .venv、venv 同样不读。已有测试报告和 Bug 单即使出现在 --docs 中也跳过。

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from config import Config, PipelineError, is_report_or_bug

SKIP_DIRS = {
    "node_modules",
    "dist",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
SKIP_FILES = {"package-lock.json"}
SKIP_SUFFIX = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".pyc",
    ".pyo",
    ".woff",
    ".woff2",
}
TEXT_SUFFIX = {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".md", ".json", ".vue", ".txt"}
PAGE_SUFFIX = {".jsx", ".tsx", ".vue", ".js", ".html"}


@dataclass
class SourceFile:
    path: str
    text: str
    kind: str


def collect(cfg: Config) -> list[SourceFile]:
    """遍历源码目录、PRD 和 --docs，返回去重后的文件。"""
    files: list[SourceFile] = []
    seen: set[str] = set()
    for rel, kind in cfg.source_kinds.items():
        base = cfg.repo_root / rel
        for path in _walk(base, cfg):
            rel_path = path.resolve().relative_to(cfg.repo_root.resolve()).as_posix()
            if rel_path in seen or _blocked(rel_path, cfg):
                continue
            text = _read_text(path)
            if text is None:
                continue
            seen.add(rel_path)
            files.append(SourceFile(rel_path, text, kind))

    _add_doc(files, seen, cfg, cfg.prd, "prd")
    for rel in cfg.docs:
        label = is_report_or_bug(rel)
        if label == "report":
            print(f"跳过已有测试报告：{rel}", flush=True)
            continue
        if label == "bug":
            print(f"跳过已有 Bug 单：{rel}", flush=True)
            continue
        _add_doc(files, seen, cfg, rel, "doc")

    _validate(files)
    order = {"frontend": 0, "backend": 1, "prd": 2, "doc": 3}
    files.sort(key=lambda item: (order.get(item.kind, 9), item.path))
    print(f"读入文件 {len(files)} 个", flush=True)
    for item in files:
        print(f"读入 {item.path}", flush=True)
    return files


def _walk(base: Path, cfg: Config) -> list[Path]:
    found: list[Path] = []
    repo = cfg.repo_root.resolve()
    for dirpath, dirnames, filenames in os.walk(base):
        current = Path(dirpath).resolve()
        rel_dir = current.relative_to(repo).as_posix()
        if _blocked(rel_dir, cfg):
            dirnames.clear()
            continue
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and not name.startswith(".")]
        for name in filenames:
            if name in SKIP_FILES or name.startswith("."):
                continue
            suffix = Path(name).suffix.lower()
            if suffix in SKIP_SUFFIX or suffix not in TEXT_SUFFIX:
                continue
            found.append(current / name)
    return found


def _blocked(rel: str, cfg: Config) -> bool:
    posix = rel.replace("\\", "/")
    work = cfg.work_dir.strip("/")
    if posix == work or posix.startswith(work + "/"):
        return True
    if posix == "pipeline/work" or posix.startswith("pipeline/work/"):
        return True
    parts = set(posix.split("/"))
    return bool(parts & SKIP_DIRS)


def _add_doc(files: list[SourceFile], seen: set[str], cfg: Config, rel: str, kind: str) -> None:
    if rel in seen:
        return
    path = cfg.repo_root / rel
    text = _read_text(path)
    if text is None:
        raise PipelineError(f"无法读取：{rel}")
    seen.add(rel)
    files.append(SourceFile(rel, text, kind))


def _read_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\x00" in data:
        return None
    for encoding in ("utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    print(f"跳过无法解码的文件：{path.name}", flush=True)
    return None


def _validate(files: list[SourceFile]) -> None:
    paths = [item.path for item in files]
    for path in paths:
        if path.endswith(".db") or "/node_modules/" in path or "/.venv/" in f"/{path}":
            raise PipelineError(f"文件列表含不应读取的路径：{path}")
    if not any(item.kind == "prd" for item in files):
        raise PipelineError("文件列表缺少 PRD")
    if not any(_is_page(item.path) for item in files if item.kind == "frontend"):
        raise PipelineError("文件列表缺少前端页面文件")
    if "backend/app.py" not in paths:
        raise PipelineError("文件列表缺少 backend/app.py")


def _is_page(rel: str) -> bool:
    parts = rel.split("/")
    if Path(rel).suffix.lower() not in PAGE_SUFFIX:
        return False
    return "pages" in parts or "page" in parts
