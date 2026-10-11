# 回复切分
#
# 职责：按 ===== 相对路径 ===== 把回复拆成文件并落盘。
# 输入：回复字符串；阶段（首次、继续定位、输出结论）。
# 输出：已写入的相对路径。非法路径不写盘，并记为失败。
#
# 本机文档写到当前目录下 AIgen-docs/。脚本写到 pipeline/work/ui/。
# 拒绝 frontend/、backend/、仓库外路径，以及下列手工文档：
#   docs/testcases/登录注册Demo-测试用例.md
#   docs/test-records/登录注册Demo-测试执行记录.md
#   docs/test-reports/登录注册Demo-测试报告.md
#   docs/bugs/BUG-001-用户名长度不足仍可注册.md

from __future__ import annotations

import re
from dataclasses import dataclass, field

from config import DOCS_DIR, Config, PipelineError, is_manual_target

_MARK = re.compile(r"^[ \t]*===== (.+?) =====[ \t]*$", re.M)
_BUG = re.compile(r"^AIgen-docs/BUG-[^/]+\.md$")
_CONCLUSION = {
    f"{DOCS_DIR}/测试执行记录.md",
    f"{DOCS_DIR}/测试报告.md",
}


@dataclass
class SplitResult:
    written: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    discarded: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def ok(self) -> bool:
        return not self.reason


def apply(text: str, stage: str, cfg: Config) -> SplitResult:
    """stage 取 first、locate、conclude。目录不存在则创建。"""
    if stage not in {"first", "locate", "conclude"}:
        raise PipelineError(f"未知阶段：{stage}")
    sections = _sections(text)
    result = SplitResult()
    if not sections:
        result.reason = "回复里没有 ===== 相对路径 ===== 分隔行"
        return result

    bodies: dict[str, str] = {}
    order: list[str] = []
    for raw_path, body in sections:
        rel = _normalize(raw_path)
        if rel is None:
            result.rejected.append(raw_path.strip())
            continue
        if rel not in bodies:
            order.append(rel)
        bodies[rel] = body

    for rel in order:
        problem = _classify(rel, stage, cfg)
        if problem == "discard":
            result.discarded.append(rel)
            continue
        if problem:
            result.rejected.append(f"{rel}（{problem}）")
            continue
        _write(cfg, rel, bodies[rel])
        result.written.append(rel)
        print(f"写入 {rel}", flush=True)

    result.reason = _reason(result, stage)
    return result


def _sections(text: str) -> list[tuple[str, str]]:
    matches = list(_MARK.finditer(text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1), text[start:end]))
    return sections


def _normalize(raw: str) -> str | None:
    text = raw.strip().strip("`").strip().replace("\\", "/")
    if not text or text.startswith("/") or (len(text) >= 2 and text[1] == ":"):
        return None
    parts = []
    for part in text.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            return None
        parts.append(part)
    if not parts:
        return None
    return "/".join(parts)


def _classify(rel: str, stage: str, cfg: Config) -> str:
    """返回空字符串表示可写，discard 表示该段丢掉，其他文字是拒绝原因。"""
    if rel == "frontend" or rel.startswith("frontend/") or rel == "backend" or rel.startswith("backend/"):
        return "拒绝写入 frontend 或 backend"
    if is_manual_target(rel):
        return "拒绝写入手工文档"
    full = (cfg.repo_root / rel).resolve()
    try:
        full.relative_to(cfg.repo_root.resolve())
    except ValueError:
        return "路径超出仓库"
    if stage in {"first", "locate"} and _is_conclusion(rel):
        return "discard"
    if not _allowed(rel, stage, cfg.work_dir):
        return "当前阶段不允许该路径"
    return ""


def _is_conclusion(rel: str) -> bool:
    return rel in _CONCLUSION or bool(_BUG.fullmatch(rel))


def _allowed(rel: str, stage: str, work_dir: str) -> bool:
    work = work_dir.strip("/")
    if stage in {"first", "locate"}:
        if stage == "first" and rel == f"{DOCS_DIR}/测试用例.md":
            return True
        if stage == "locate" and rel == f"{DOCS_DIR}/测试用例.md":
            return True
        prefix = f"{work}/ui/"
        if rel.startswith(prefix) and rel.endswith(".py"):
            name = rel[len(prefix):]
            return "/" not in name and name != ""
        return False
    return _is_conclusion(rel)


def _write(cfg: Config, rel: str, body: str) -> None:
    text = _unwrap(body)
    path = cfg.repo_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _unwrap(body: str) -> str:
    text = body.strip("\n")
    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        text = "\n".join(lines[1:-1])
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def _reason(result: SplitResult, stage: str) -> str:
    lines: list[str] = []
    if result.discarded:
        listed = "、".join(result.discarded)
        lines.append(f"已丢弃当前阶段不能写的文档：{listed}")
        lines.append("请只重发用例和页面脚本。")
    if result.rejected:
        lines.append("以下路径未写盘：" + "、".join(result.rejected))
    if stage == "first" and f"{DOCS_DIR}/测试用例.md" not in result.written:
        lines.append(f"缺少 {DOCS_DIR}/测试用例.md")
    if stage == "locate" and not any(path.endswith(".py") for path in result.written):
        lines.append("继续定位时需要新的页面脚本")
    if stage == "conclude" and not result.written and not lines:
        lines.append("没有可落盘的结论文档")
    return "\n".join(lines)
