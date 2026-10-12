# 配置
#
# 职责：读取命令行和环境变量，整理成一份运行配置。缺必选项时抛出错误，由入口退出。
# 输入：命令行参数；环境变量 LLM_API_KEY。
# 输出：Config。密钥只留在对象里，不打印、不写入仓库。
#
# 本机默认（Windows，仓库根目录 B:\cs\Internship，在该目录执行 python pipeline/run.py）：
#   --source frontend --source backend（目录不存在则退出）
#   --prd docs/prd/登录注册Demo-PRD.md
#   --web-base http://localhost:5173
#   --api-base http://localhost:5000
#   --channel all
#   --llm-base-url https://api.openai.com/v1
#   --llm-model gpt-4o-mini
#   --codegen-retries 3
#   --locate-rounds 7
#   --timeout 120
#   --max-tokens 16384
#   --work-dir pipeline/work
#   --docs 无
#   --req 无
#   --headed 关闭
#   --dry-run 关闭
#   --verbose 关闭。加上后只在终端回显发给模型的消息，以及模型回复的用例和脚本
#   对话日志：工作目录 dialogue.log（默认 pipeline/work/dialogue.log）
#   每次运行覆盖。记录连通性探测、用户消息和模型回复，不写密钥、请求头和请求 URL
#   文档目录：当前目录下 AIgen-docs/
#   脚本：pipeline/work/ui/    截图：pipeline/work/screenshots/
#   密钥：只读环境变量 LLM_API_KEY

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

DOCS_DIR = "AIgen-docs"
DEFAULT_SOURCES = ("frontend", "backend")
DEFAULT_PRD = "docs/prd/登录注册Demo-PRD.md"
DEFAULT_WEB = "http://localhost:5173"
DEFAULT_API = "http://localhost:5000"
DEFAULT_LLM_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 16384
DEFAULT_WORK = "pipeline/work"

# 手工文档，流水线只读时跳过报告和 Bug 单，写盘时整份拒绝。
MANUAL_DOCS = (
    "docs/testcases/登录注册Demo-测试用例.md",
    "docs/test-records/登录注册Demo-测试执行记录.md",
    "docs/test-reports/登录注册Demo-测试报告.md",
    "docs/bugs/BUG-001-用户名长度不足仍可注册.md",
)
MANUAL_DOC_DIRS = (
    "docs/prd/",
    "docs/srs/",
    "docs/testcases/",
    "docs/test-records/",
    "docs/test-reports/",
    "docs/bugs/",
)


class PipelineError(Exception):
    """入口捕获后打印到标准错误并以非 0 退出。"""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class Config:
    sources: list[str]
    prd: str
    api_key: str
    docs: list[str]
    web_base: str
    api_base: str
    requirements: list[str]
    channel: str
    llm_base_url: str
    llm_model: str
    max_tokens: int
    codegen_retries: int
    locate_rounds: int
    timeout: int
    headed: bool
    work_dir: str
    dry_run: bool
    verbose: bool
    repo_root: Path
    source_kinds: dict[str, str]

    def __repr__(self) -> str:
        # 避免日志或调试把密钥打出来。
        hidden = "***" if self.api_key else ""
        return (
            f"Config(sources={self.sources!r}, prd={self.prd!r}, api_key={hidden!r}, "
            f"channel={self.channel!r}, model={self.llm_model!r}, dry_run={self.dry_run!r})"
        )

    @property
    def docs_dir(self) -> Path:
        return self.repo_root / DOCS_DIR

    @property
    def work_path(self) -> Path:
        return _inside_repo(self.repo_root, self.work_dir)

    @property
    def ui_dir(self) -> Path:
        return self.work_path / "ui"

    @property
    def screenshot_dir(self) -> Path:
        return self.work_path / "screenshots"


def load(argv: list[str] | None = None) -> Config:
    """解析参数。argv 为空时使用 sys.argv，并套用本机默认目录。"""
    parser = argparse.ArgumentParser(description="测试流水线")
    parser.add_argument("--source", action="append", default=None, help="前端或后端目录，可重复")
    parser.add_argument("--prd", default=DEFAULT_PRD, help="PRD 路径")
    parser.add_argument("--docs", action="append", default=None, help="追加到首轮消息的文档，可重复")
    parser.add_argument("--web-base", default=DEFAULT_WEB, help="前端地址")
    parser.add_argument("--api-base", default=DEFAULT_API, help="账号服务地址")
    parser.add_argument("--req", action="append", dest="requirements", default=None, help="需求编号，可重复")
    parser.add_argument("--channel", default="all", choices=("api", "ui", "all"), help="api、ui 或 all")
    parser.add_argument("--llm-base-url", default=DEFAULT_LLM_URL, help="模型接口地址")
    parser.add_argument("--llm-model", default=DEFAULT_MODEL, help="模型名")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="单次回复的最大 token 数，不能超过模型上限",
    )
    parser.add_argument("--codegen-retries", type=int, default=3, help="页面脚本未通过检查时的重试次数")
    parser.add_argument("--locate-rounds", type=int, default=7, help="保留参数。页面脚本只执行一次，不再按此重跑")
    parser.add_argument("--timeout", type=int, default=120, help="单次 HTTP 或单条页面用例的超时秒数")
    parser.add_argument("--headed", action="store_true", help="浏览器可见")
    parser.add_argument("--work-dir", default=DEFAULT_WORK, help="脚本、截图和本轮结果目录")
    parser.add_argument("--dry-run", action="store_true", help="检查通过后停止，不启动服务")
    parser.add_argument("--verbose", action="store_true", help="在终端回显发给模型的消息和模型回复，不控制对话日志")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    repo = Path.cwd().resolve()
    sources = list(args.source) if args.source else list(DEFAULT_SOURCES)
    prd = _rel_text(args.prd)
    docs = [_rel_text(item) for item in (args.docs or [])]
    requirements = [item.strip() for item in (args.requirements or []) if item.strip()]

    _require_url(args.web_base, "前端地址")
    _require_url(args.api_base, "账号服务地址")
    _require_url(args.llm_base_url, "模型接口地址")
    if args.codegen_retries < 0:
        raise PipelineError("--codegen-retries 不能小于 0")
    if args.locate_rounds < 0:
        raise PipelineError("--locate-rounds 不能小于 0")
    if args.timeout <= 0:
        raise PipelineError("--timeout 必须大于 0")
    if args.max_tokens <= 0:
        raise PipelineError("--max-tokens 必须大于 0")
    if not args.llm_model.strip():
        raise PipelineError("缺少模型名")

    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise PipelineError("缺少环境变量 LLM_API_KEY")

    kinds: dict[str, str] = {}
    missing: list[str] = []
    for raw in sources:
        rel = _rel_text(raw)
        path = _inside_repo(repo, rel)
        if not path.is_dir():
            missing.append(rel)
            continue
        kind = _source_kind(path)
        if not kind:
            raise PipelineError(f"无法判断前端或后端目录：{rel}")
        kinds[path.relative_to(repo).as_posix()] = kind
    if missing:
        raise PipelineError("缺少目录：" + "、".join(missing))
    if "frontend" not in kinds.values():
        raise PipelineError("缺少前端目录")
    if "backend" not in kinds.values():
        raise PipelineError("缺少后端目录")

    prd_path = _inside_repo(repo, prd)
    if not prd_path.is_file():
        raise PipelineError(f"缺少 PRD：{prd}")

    kept_docs: list[str] = []
    for rel in docs:
        path = _inside_repo(repo, rel)
        if not path.is_file():
            raise PipelineError(f"缺少文档：{rel}")
        kept_docs.append(path.relative_to(repo).as_posix())

    work_rel = _rel_text(args.work_dir)
    work_path = _inside_repo(repo, work_rel)

    return Config(
        sources=list(kinds.keys()),
        prd=prd_path.relative_to(repo).as_posix(),
        api_key=api_key,
        docs=kept_docs,
        web_base=args.web_base.rstrip("/"),
        api_base=args.api_base.rstrip("/"),
        requirements=requirements,
        channel=args.channel,
        llm_base_url=args.llm_base_url.rstrip("/"),
        llm_model=args.llm_model.strip(),
        max_tokens=args.max_tokens,
        codegen_retries=args.codegen_retries,
        locate_rounds=args.locate_rounds,
        timeout=args.timeout,
        headed=bool(args.headed),
        work_dir=work_path.relative_to(repo).as_posix(),
        dry_run=bool(args.dry_run),
        verbose=bool(args.verbose),
        repo_root=repo,
        source_kinds=kinds,
    )


def _rel_text(value: str) -> str:
    return value.strip().replace("\\", "/")


def _require_url(value: str, label: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise PipelineError(f"{label}无效：{value}")


def _inside_repo(repo: Path, rel: str) -> Path:
    """把相对路径限制在仓库内。绝对路径和 .. 直接拒绝。"""
    text = rel.strip().replace("\\", "/")
    if not text or text.startswith("/") or _has_drive(text):
        raise PipelineError(f"路径必须相对仓库根目录：{rel}")
    parts = []
    for part in text.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise PipelineError(f"路径超出仓库：{rel}")
        parts.append(part)
    if not parts:
        raise PipelineError(f"路径无效：{rel}")
    full = (repo.joinpath(*parts)).resolve()
    try:
        full.relative_to(repo.resolve())
    except ValueError as exc:
        raise PipelineError(f"路径超出仓库：{rel}") from exc
    return full


def _has_drive(text: str) -> bool:
    return len(text) >= 2 and text[1] == ":"


def _source_kind(path: Path) -> str:
    name = path.name.casefold()
    if name in {"frontend", "web", "client"}:
        return "frontend"
    if name in {"backend", "server"}:
        return "backend"
    if (path / "package.json").is_file() and (path / "src").is_dir():
        return "frontend"
    if (path / "app.py").is_file():
        return "backend"
    return ""


def is_report_or_bug(rel: str) -> str:
    """返回 report、bug，或空字符串。用于跳过已有测试报告和 Bug 单。"""
    posix = rel.replace("\\", "/")
    name = posix.rsplit("/", 1)[-1]
    if "/test-reports/" in f"/{posix}" or "测试报告" in name:
        return "report"
    if "/bugs/" in f"/{posix}" or name.startswith("BUG-"):
        return "bug"
    return ""


def is_manual_target(rel: str) -> bool:
    posix = rel.replace("\\", "/")
    if posix in MANUAL_DOCS:
        return True
    return any(posix.startswith(prefix) for prefix in MANUAL_DOC_DIRS)
