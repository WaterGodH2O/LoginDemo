# 页面脚本检查
#
# 职责：执行前检查已落盘的页面脚本。
# 输入：pipeline/work/ui/*.py、对应用例的预期原文、剩余重试次数。
# 输出：通过的脚本路径，或一条失败原因。任一失败都不执行该轮页面脚本。
#
# 检查：compile 通过；字符串字面量含该用例「」里的提示；不出现跳过测试。
# 提示原文只取用例预期里的「」或引号，不另设固定词表。
# 次数用尽后由入口退出，不启动 Demo。

from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass, field

from cases import UiCase
from config import Config

_SKIP = re.compile(
    r"pytest\s*\.\s*(?:skip|importorskip)|mark\s*\.\s*skip|unittest\s*\.\s*skip|SkipTest",
    re.I,
)
_QUOTED = re.compile(r"[「\"]([^」\"]+)[」\"]")
_PRODUCT_PATH = re.compile(r"""['"](?:\./|\.\./)?(?:frontend|backend)[/\\]""")


@dataclass
class CheckResult:
    ok: bool
    scripts: list[str] = field(default_factory=list)
    reason: str = ""


def check(ui_cases: list[UiCase], cfg: Config, retries_left: int) -> CheckResult:
    """只编译，不执行。没有页面用例时直接通过。"""
    if not ui_cases:
        return CheckResult(True, [], "")
    problems: list[str] = []
    scripts: list[str] = []
    for case in ui_cases:
        problems.extend(_one(case, cfg))
        if case.script:
            scripts.append(case.script)
    if problems:
        lines = problems + [f"剩余重试次数：{retries_left}"]
        return CheckResult(False, [], "\n".join(lines))
    return CheckResult(True, scripts, "")


def _one(case: UiCase, cfg: Config) -> list[str]:
    if not case.script:
        return [f"{case.id} 没有对应脚本"]
    path = cfg.repo_root / case.script
    if not path.is_file():
        return [f"{case.id} 缺少脚本 {case.script}"]
    source = path.read_text(encoding="utf-8")
    # 语法不过则后面的文本检查没有意义。
    try:
        compile(source, case.script, "exec")
    except SyntaxError as exc:
        return [f"{case.id} 无法编译：第 {exc.lineno} 行 {exc.msg}"]

    found: list[str] = []
    missing = [text for text in _needles(case.expected) if not _literal_has(source, text)]
    if missing:
        shown = "、".join(f"「{item}」" for item in missing)
        found.append(f"{case.id} 的脚本 {case.script} 未包含预期原文{shown}")
    if _SKIP.search(_code(source)):
        found.append(f"{case.id} 含有跳过测试")
    if _PRODUCT_PATH.search(source):
        found.append(f"{case.id} 的脚本指向 frontend 或 backend")
    return found


def _needles(expected: str) -> list[str]:
    """从预期说明里取出断言必须包含的提示原文。"""
    quoted: list[str] = []
    for match in _QUOTED.finditer(expected):
        text = match.group(1).strip()
        if text and text not in quoted:
            quoted.append(text)
    return quoted


def _literal_has(source: str, expected: str) -> bool:
    if not expected:
        return False
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type != tokenize.STRING:
                continue
            if expected in tok.string:
                return True
            try:
                value = ast.literal_eval(tok.string)
            except (SyntaxError, ValueError):
                continue
            if isinstance(value, str) and expected in value:
                return True
    except tokenize.TokenError:
        return False
    return False


def _code(source: str) -> str:
    parts: list[str] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type in {tokenize.NL, tokenize.NEWLINE}:
                parts.append("\n")
            elif tok.type != tokenize.ENDMARKER:
                parts.append(tok.string)
                parts.append(" ")
    except tokenize.TokenError:
        return source
    return "".join(parts)
