# 轮次控制
#
# 职责：看回复第一行，决定继续定位还是输出结论。
# 输入：回复第一行和余下正文；本轮是否全部通过；已用定位轮数；locate_rounds。
# 输出：继续定位或输出结论。第一行不是这两种决定时，要求重发。
#
# 本机 --locate-rounds 默认 2。
# 全部用例已通过时动作为输出结论，不消耗定位轮数。
# 继续定位的余下内容应是新的页面脚本。输出结论时落盘三份文档。

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DECIDE_LOCATE = "决定：继续定位"
DECIDE_CONCLUDE = "决定：输出结论"

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


def parse_decision(reply: str, all_passed: bool, used: int, limit: int) -> Decision:
    """全部通过时只接受输出结论，并且 consume_round 为假。"""
    line = first_line(reply)
    if all_passed:
        if line == DECIDE_CONCLUDE:
            return Decision("conclude", False, "")
        return Decision("invalid", False, "全部用例已通过，只接受「决定：输出结论」")
    if line == DECIDE_CONCLUDE:
        return Decision("conclude", False, "")
    if line == DECIDE_LOCATE:
        if used >= limit:
            return Decision("invalid", False, "定位轮数已用尽，只接受「决定：输出结论」")
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
    """结论文档缺文件或缺栏目时，返回需要重发的原因。"""
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
    if record in written:
        problems.extend(_need_words(repo_root, record, ("步骤", "预期", "实际")))
        record_text = (repo_root / record).read_text(encoding="utf-8") if (repo_root / record).is_file() else ""
        if "通过" not in record_text and "失败" not in record_text:
            problems.append(f"{record} 缺少：通过或失败")
    if report in written:
        problems.extend(_need_words(repo_root, report, ("环境", "通过", "失败", "结论", web_base, api_base)))
    for path in bugs:
        problems.extend(
            _need_words(repo_root, path, ("编号", "标题", "严重程度", "所属需求", "关联用例", "复现", "预期", "实际"))
        )
    return "\n".join(problems)


def _need_words(repo_root: Path, rel: str, words: tuple[str, ...]) -> list[str]:
    path = repo_root / rel
    if not path.is_file():
        return [f"缺少 {rel}"]
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return [f"{rel} 是空文件"]
    absent = [word for word in words if word not in text]
    if not absent:
        return []
    return [f"{rel} 缺少：" + "、".join(absent)]
