# 轮次控制
#
# 职责：看回复第一行，决定是否输出结论。
# 输入：回复第一行和余下正文。
# 输出：输出结论，或要求重发。页面脚本只执行一次，不再接受继续定位。
#
# 规格说明书和测试用例落盘后即进入下一步。输出结论时只检查文件是否写出。

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DECIDE_LOCATE = "决定：继续定位"
DECIDE_CONCLUDE = "决定：输出结论"
SRS_REL = "AIgen-docs/需求规格说明书.md"

_BUG_NAME = re.compile(r"^AIgen-docs/BUG-[^/]+\.md$")


@dataclass
class Decision:
    action: str
    consume_round: bool
    message: str


def first_line(reply: str) -> str:
    text = reply.lstrip("\ufeff").strip()
    if not text:
        return ""
    return text.splitlines()[0].strip()


def parse_decision(
    reply: str,
    all_passed: bool,
    used: int,
    limit: int,
    allow_locate: bool = False,
) -> Decision:
    """默认只接受输出结论。allow_locate 为真时才允许继续定位。"""
    del used, limit
    line = first_line(reply)
    if line == DECIDE_CONCLUDE:
        return Decision("conclude", False, "")
    if not allow_locate:
        return Decision("invalid", False, "页面脚本只执行一次，只接受「决定：输出结论」")
    if all_passed:
        return Decision("invalid", False, "全部用例已通过，只接受「决定：输出结论」")
    if line == DECIDE_LOCATE:
        return Decision("locate", True, "")
    return Decision(
        "invalid",
        False,
        "回复第一行只能是「决定：继续定位」或「决定：输出结论」",
    )


def conclusion_gap(
    repo_root: Path,
    written: list[str],
    web_base: str,
    api_base: str,
    had_failures: bool,
) -> str:
    """结论文档缺文件或正文为空时，返回需要重发的原因。"""
    del web_base, api_base
    missing: list[str] = []
    record = "AIgen-docs/测试执行记录.md"
    report = "AIgen-docs/测试报告.md"
    bugs = [path for path in written if _BUG_NAME.fullmatch(path)]
    if record not in written:
        missing.append(record)
    if report not in written:
        missing.append(report)
    if had_failures and not bugs:
        missing.append("AIgen-docs/BUG-编号-标题.md")
    problems = [f"缺少 {path}" for path in missing]
    for rel in [record, report, *bugs]:
        if rel not in written:
            continue
        path = repo_root / rel
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            problems.append(f"{rel} 是空文件")
    return "\n".join(problems)
