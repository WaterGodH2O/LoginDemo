# 结果消息
#
# 职责：把本轮执行结果拼成下一条用户消息。
# 输入：页面执行结果、接口执行结果、用例预期原文。
# 输出：一条用户消息。预期原文来自用例，实际结果来自页面或接口执行。
#
# 通过的用例只保留编号和「通过」。失败项带上脚本或请求、退出码、截图和输出摘录。
# 消息末尾只接受「决定：输出结论」。页面脚本只执行一次，不再要求继续定位。
# 末尾附上已有执行记录、测试报告和 Bug 单原文，只作版式示例。
# 本机前端 http://localhost:5173 ，账号服务 http://localhost:5000。
# 页面脚本目录 pipeline/work/ui/ ，截图目录 pipeline/work/screenshots/。

from __future__ import annotations

from api_run import ApiResult
from config import Config
from doc_examples import BUG, RECORD, REPORT
from loop import DECIDE_CONCLUDE
from ui_run import UiResult

_EXCERPT = 1200


def build(
    ui_results: list[UiResult],
    api_results: list[ApiResult],
    cfg: Config,
    force_conclude: bool,
    force_reason: str = "",
) -> str:
    """force_conclude 为真时，消息只接受输出结论。"""
    blocks: list[str] = []
    for item in ui_results:
        blocks.append(_pass_line(item.case_id) if item.passed else _ui_failure(item))
    for item in api_results:
        blocks.append(_pass_line(item.case_id) if item.passed else _api_failure(item))
    blocks.append(_footer(cfg, force_conclude, force_reason))
    blocks.append(_examples())
    return "\n".join(block for block in blocks if block).rstrip() + "\n"


def _examples() -> str:
    return "\n".join(
        [
            "下面三份是仓库里已有文档，只作版式示例。",
            "通过、失败、步骤、预期、实际和统计以本条消息中的执行结果为准。",
            "不要照抄示例里的结论、日期和数量。环境写本次前端地址和账号服务地址。",
            "文件仍用上面的 AIgen-docs 分隔行，不要写成 docs/ 下的原路径。",
            "【示例：测试执行记录】",
            RECORD.strip(),
            "【示例：测试报告】",
            REPORT.strip(),
            "【示例：Bug 单】",
            BUG.strip(),
        ]
    )


def _pass_line(case_id: str) -> str:
    return f"用例：{case_id}\n结果：通过\n"


def _ui_failure(item: UiResult) -> str:
    return "\n".join(
        [
            "【执行结果】",
            f"用例：{item.case_id}",
            f"需求：{item.requirement}",
            f"脚本：{item.script}",
            "结果：失败",
            f"预期：{item.expected}",
            f"实际：{item.actual}",
            f"退出码：{item.exit_code}",
            f"截图：{item.screenshot}",
            "输出摘录：",
            _excerpt(item.stdout),
            "",
        ]
    )


def _api_failure(item: ApiResult) -> str:
    # 接口失败沿用同一版式：脚本行改为方法和 URL，退出码改为 HTTP 状态码。
    return "\n".join(
        [
            "【执行结果】",
            f"用例：{item.case_id}",
            f"需求：{item.requirement}",
            f"脚本：{item.method} {item.url}",
            "结果：失败",
            f"预期：{item.expected}",
            f"实际：{item.actual}",
            f"退出码：{item.status}",
            "截图：无",
            "输出摘录：",
            _excerpt(item.body),
            "",
        ]
    )


def _excerpt(text: str) -> str:
    body = (text or "").strip()
    if len(body) <= _EXCERPT:
        return body
    return body[:_EXCERPT] + "\n...过长则截断..."


def _footer(cfg: Config, force_conclude: bool, force_reason: str) -> str:
    docs = "\n".join(
        [
            "===== AIgen-docs/测试执行记录.md =====",
            "===== AIgen-docs/测试报告.md =====",
            "===== AIgen-docs/BUG-编号-标题.md =====",
            "测试执行记录按用例写下步骤、预期、实际和通过或失败。",
            "测试报告包含环境、通过与失败统计、失败说明和结论。",
            f"环境写明前端 {cfg.web_base} 与账号服务 {cfg.api_base}。",
            "同一需求的页面失败和接口失败合并为一张 Bug 单。",
            "Bug 单包含编号、标题、严重程度、所属需求、关联用例、复现步骤、预期结果、实际结果。",
            "实际结果写出上面的执行结果。",
        ]
    )
    del force_conclude
    lead = force_reason or f"请输出结论。回复的第一行只能是「{DECIDE_CONCLUDE}」。"
    extra = "没有失败时不要写 Bug 单。" if "全部用例已通过" in (force_reason or "") else "请给出失败需求对应的 Bug 单。"
    return "\n".join(
        [
            "每个页面用例的 Playwright 脚本只执行一次。不要再写脚本，不要继续定位。",
            lead,
            f"回复的第一行只能是「{DECIDE_CONCLUDE}」。",
            "随后按分隔行给出文档：",
            docs,
            extra,
        ]
    )
