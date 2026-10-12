# 消息拼装
#
# 职责：把文件列表拼成一条用户消息。使用普通文本，不走文件上传接口。
# 输入：文件列表；requirements、channel；失败后的重发原因。
# 输出：一条用户消息。后续轮的执行结果由结果消息模块另拼，这里不再附带源码。
#
# 本机默认通道 all，需求编号默认不限制。
# 页面脚本目录 pipeline/work/ui/，文档目录 AIgen-docs/。
# 前端 http://localhost:5173，后端 http://localhost:5000。
# 首轮只要求写需求规格说明书。下一轮再根据该说明书写测试用例和页面脚本。
# 版式分别对齐 docs/srs 与 docs/testcases，示例不是全部条目。

from __future__ import annotations

from pathlib import Path

from collect import SourceFile
from config import DOCS_DIR, Config
from doc_examples import SRS_SAMPLE, TESTCASES

LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".css": "css",
    ".html": "html",
    ".md": "markdown",
    ".json": "json",
    ".vue": "vue",
    ".txt": "text",
}


def first_message(files: list[SourceFile], cfg: Config) -> str:
    """首轮四段：目录树、逐文件原文、必要时改用 file 标签、最后是任务说明。"""
    parts = [_tree(files), ""]
    for item in files:
        parts.append(_file_block(item.path, item.text))
        parts.append("")
    parts.append(_srs_task())
    return "\n".join(parts).rstrip() + "\n"


def cases_message(cfg: Config, srs_text: str) -> str:
    """第二轮：附上已落盘的规格说明书，要求据此写用例和页面脚本。"""
    lead = "\n".join(
        [
            "下面是你刚写好的需求规格说明书。接下来只根据这份说明书写测试用例，并为每条页面用例写 Playwright 脚本。",
            "不要重写需求规格说明书，也不要写测试执行记录、测试报告或 Bug 单。",
            "",
        ]
    )
    return lead + _file_block(f"{DOCS_DIR}/需求规格说明书.md", srs_text) + "\n\n" + _task(cfg)


def locator_lines() -> list[str]:
    """表单定位。get_by_label 默认子串匹配，短标签会命中包含它的长标签。"""
    return [
        'get_by_label 默认按子串匹配。get_by_label("密码") 会同时选中「密码」和「确认密码」，fill 抛出 strict mode violation，脚本在检查页面提示之前退出。这是脚本错误，不是页面缺少预期文案。',
        '定位必须精确：page.get_by_label("用户名", exact=True)、page.get_by_label("密码", exact=True)、page.get_by_label("确认密码", exact=True)。按钮用 get_by_role("button", name="注册") 或 name="登录"。',
    ]


def fix_message(reason: str, *, scripts_only: bool = False) -> str:
    """用例或页面脚本未通过时，交回原因。scripts_only 时不要让模型重写测试用例。"""
    if scripts_only:
        lead = [
            "上一次输出不能用。请只重发下面点名的页面脚本。",
            "不要重发已经通过的脚本，也不要重发测试用例。",
        ]
    else:
        lead = ["上一次输出不能用。请只重发测试用例和未通过的页面脚本。"]
    lines = lead + [
        "不要重写需求规格说明书，也不要写测试执行记录、测试报告或 Bug 单。",
        "点名的脚本路径里，Python 字符串必须包含该编号预期中「」里的每一句提示，不要改字，写在注释里不算，也不要写到别的编号的文件里。",
        "不要跳过测试。分隔行格式：===== 相对路径 =====",
        *locator_lines(),
        reason.strip(),
    ]
    return "\n".join(lines).rstrip() + "\n"


def srs_fix_message(reason: str) -> str:
    """规格说明书未通过时，只要求重发这一份。"""
    lines = [
        "上一次需求规格说明书不能用。请只重发这一份。",
        "不要写测试用例、页面脚本、测试执行记录、测试报告或 Bug 单。",
        f"分隔行：===== {DOCS_DIR}/需求规格说明书.md =====",
        "每条需求用四级标题，标题里写需求编号。字段用两列表格，包含需求描述、前置条件、输入、预期结果、优先级、PRD 来源。",
        reason.strip(),
    ]
    return "\n".join(lines).rstrip() + "\n"


def decision_fix_message(reason: str) -> str:
    """第一行不是允许的决定时，只重复该用哪一行。"""
    lines = [
        "上一次回复的第一行不能用。",
        reason.strip(),
        "请按上面的要求重发。分隔行格式：===== 相对路径 =====",
    ]
    return "\n".join(lines).rstrip() + "\n"


def conclusion_fix_message(reason: str) -> str:
    """结论文档未通过时，要求重发三份文档，不要退回用例和脚本。"""
    lines = [
        "上一次结论不能用。请重新输出结论。",
        "回复的第一行只能是「决定：输出结论」。",
        "随后按分隔行给出测试执行记录、测试报告；有失败用例时再给 Bug 单。",
        "不要重发测试用例和页面脚本。",
        "分隔行格式：===== 相对路径 =====",
        reason.strip(),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _tree(files: list[SourceFile]) -> str:
    root: dict = {}
    for item in files:
        node = root
        parts = item.path.split("/")
        for part in parts[:-1]:
            child = node.setdefault(part, {})
            if child is None:
                child = {}
                node[part] = child
            node = child
        node[parts[-1]] = None
    lines = ["【目录】"]

    def walk(node: dict, depth: int) -> None:
        names = sorted(node, key=lambda name: (node[name] is None, name.lower()))
        for name in names:
            indent = "  " * depth
            child = node[name]
            if child is None:
                lines.append(f"{indent}{name}")
            else:
                lines.append(f"{indent}{name}/")
                walk(child, depth + 1)

    walk(root, 0)
    return "\n".join(lines)


def _file_block(path: str, text: str) -> str:
    body = text.replace("\r\n", "\n").replace("\r", "\n")
    if body.endswith("\n"):
        body = body[:-1]
    # 原文里已有围栏时，改用 file 标签，避免和消息里的代码块打架。
    if "```" in body:
        return f"【文件 {path}】\n<file path=\"{path}\">\n{body}\n</file>"
    lang = LANG.get(Path(path).suffix.lower(), "")
    fence = f"```{lang}" if lang else "```"
    return f"【文件 {path}】\n{fence}\n{body}\n```"


def _sample_scripts(web_base: str, work_dir: str) -> tuple[str, str]:
    """首轮示例脚本。提示字符串和文件名必须对上检查器要的那一条。"""

    def one(case_id: str, expected: str, username: str) -> str:
        shot = f"{work_dir}/screenshots/{case_id}.png"
        return "\n".join(
            [
                "import os",
                "import sys",
                "from playwright.sync_api import sync_playwright",
                "",
                f'CASE_ID = "{case_id}"',
                f'EXPECTED = "{expected}"',
                f'WEB = os.environ.get("WEB_BASE", "{web_base}")',
                'HEADED = os.environ.get("HEADED") == "1"',
                f'SHOT = os.environ.get("PIPELINE_SCREENSHOT", "{shot}")',
                "",
                "def main() -> int:",
                "    with sync_playwright() as playwright:",
                "        browser = playwright.chromium.launch(headless=not HEADED)",
                "        page = browser.new_page()",
                "        ok = False",
                "        try:",
                '            page.goto(WEB.rstrip("/") + "/register", wait_until="domcontentloaded")',
                f'            page.get_by_label("用户名", exact=True).fill("{username}")',
                '            page.get_by_label("密码", exact=True).fill("Pass1234")',
                '            page.get_by_label("确认密码", exact=True).fill("Pass1234")',
                '            page.get_by_role("button", name="注册").click()',
                "            page.wait_for_timeout(1000)",
                '            ok = EXPECTED in page.locator("body").inner_text()',
                "        finally:",
                "            page.screenshot(path=SHOT, full_page=True)",
                "            browser.close()",
                '    print("结果：通过" if ok else "结果：失败")',
                "    return 0 if ok else 1",
                "",
                'if __name__ == "__main__":',
                "    sys.exit(main())",
            ]
        )

    return (
        one("TC-UI-REG-002", "用户名长度不足", "abcde"),
        one("TC-UI-REG-003", "注册成功，请登录", "user01"),
    )


def _srs_task() -> str:
    """首轮只写规格说明书。条目从 PRD 归纳，示例只示范一条的版式。"""
    return "\n".join(
        [
            "根据消息里的 PRD 写出需求规格说明书。这一步不要写测试用例、页面脚本、测试执行记录、测试报告或 Bug 单。",
            "不要写 frontend/ 或 backend/ 下的文件。",
            "分隔行只能是这种，路径用相对路径：",
            f"===== {DOCS_DIR}/需求规格说明书.md =====",
            "格式对齐 docs/srs/登录注册Demo-需求规格说明书.md。",
            "标题写明需求规格说明书。文档按这个顺序写：总体描述、功能需求（注册、登录、首页与退出）、非功能需求、需求追踪、文档信息。",
            "每条需求一个四级标题，标题以需求编号开头。字段用两列表格，行名依次为：需求描述、前置条件、输入、预期结果、优先级、PRD 来源。优先级只写高或中。",
            "内容从本条消息中的 PRD 归纳。PRD 第 4 节写明不包含的功能不要写。",
            "预期按 PRD 写。源码里没有用户名长度校验时，不要据此把不足 6 位改成注册成功。",
            "需求追踪用表格把 PRD 位置对应到需求编号。",
            "下面只示范一条的版式。PRD 里的其余规则按同样表格写全，不要只交这一条。",
            "【示例：一条需求】",
            SRS_SAMPLE.strip(),
        ]
    )


def _task(cfg: Config) -> str:
    if cfg.channel == "api":
        opening = "根据上面的需求规格说明书写接口测试用例。一次写完。"
    else:
        opening = "根据上面的需求规格说明书写测试用例。每条页面用例再写一个 Playwright 脚本。一次写完。"
    lines = [
        opening,
        "每个页面用例的脚本只执行一次，执行后直接根据结果写结论，不会再要求你改脚本做第二轮定位。编号和「」里的提示必须这次写对。",
        "不要重写需求规格说明书。不要写测试执行记录、测试报告、Bug 单。不要写 frontend/ 或 backend/ 下的文件。",
        "分隔行只能是这种，路径用相对路径：",
        f"===== {DOCS_DIR}/测试用例.md =====",
        f"===== {cfg.work_dir}/ui/test_tc_ui_reg_002.py =====",
        "顺序固定：先写完测试用例文件，json 放在该文件最后；再按编号写完全部页面脚本，然后结束。",
        "格式对齐 docs/testcases/登录注册Demo-测试用例.md。先写手工用例，再写接口用例。",
        "每条用例一个四级标题，标题以 TC- 编号开头。字段用两列表格，行名依次为：对应需求、测试方式、优先级、前置条件、步骤、预期结果。",
        "测试方式只写手工或接口。对应需求只写规格说明书里的编号，多条用顿号隔开。",
        "「」里只放页面或接口上的短提示，不要把整段说明放进「」。",
        "预期按 PRD 和上面的需求规格说明书写。源码里没有长度校验时，不要据此把不足 6 位改成注册成功。",
        "接口用例先按上面的表格写在正文里。步骤写明方法、/api/ 路径和请求体，预期结果写明 HTTP 状态码。",
        "同一批接口用例再写入文件末尾的一个 json 数组，供执行。不要插在用例中间，不要写成 Playwright。",
        "json 字段：id、requirement、channel、method、path、body、expected_status、expected_text。expected_status 写整数。expected_text 使用预期里「」中的短提示。",
    ]
    if cfg.channel != "api":
        lines.extend(
            [
                "每个页面用例恰好一个 py 文件。文件名是 test_ 加编号小写，连字符改下划线。",
                "test_tc_ui_reg_002.py 只对应 TC-UI-REG-002，断言提示是「用户名长度不足」，不能写成「请输入用户名」或「注册成功」。",
                "test_tc_ui_reg_003.py 只对应 TC-UI-REG-003，断言提示是「注册成功，请登录」，不能写成用户名长度不足。",
                "Python 字符串必须包含该用例预期里每一对「」中的原文，不能改字，不能放进别的编号的文件，写在注释里不算。",
                "一条预期有多句「」时，这几句都要出现在同一个脚本里。例如「请输入密码」「请再次输入密码」「两次输入的密码不一致」都写进 test_tc_ui_reg_005.py。",
                "预期含「用户名长度不足」或所属需求为 REQ-REG-002 时，字符串保留「用户名长度不足」，禁止断言「注册成功」。",
                "使用 Playwright 同步 API。脚本必须能被 Python 编译。不要跳过测试。字符串里不要出现 frontend/ 或 backend/ 路径。",
                "退出码 0 表示页面文本包含这些提示，退出码 1 表示没有。",
                f"WEB_BASE 缺省 {cfg.web_base}。HEADED 为 1 时浏览器可见，否则无头。",
                f"截图写到 {cfg.work_dir}/screenshots/用例编号.png。",
                *locator_lines(),
                "只做本条步骤。登录用例打开 /login。",
            ]
        )
    if cfg.requirements:
        lines.append("只处理这些需求编号：" + "、".join(cfg.requirements))
    if cfg.channel == "api":
        lines.append("通道范围：只写接口用例，放进文末 json。不要写页面脚本。")
    elif cfg.channel == "ui":
        lines.append("通道范围：只写页面用例和对应脚本。文末 json 写 []，不要照抄示例里的接口对象。")
    lines.append("下面只示范版式，不是要交的全部用例。不要照抄示例账号。覆盖要求在示例后面。")
    lines.append("【示例：测试用例】")
    lines.append(TESTCASES.strip())
    if cfg.channel != "api":
        first, second = _sample_scripts(cfg.web_base, cfg.work_dir)
        lines.append("测试用例文件到 json 结束。下面每个页面用例各一个脚本，提示不能互换，也不能写进同一个文件。")
        lines.append(f"===== {cfg.work_dir}/ui/test_tc_ui_reg_002.py =====")
        lines.append(first)
        lines.append(f"===== {cfg.work_dir}/ui/test_tc_ui_reg_003.py =====")
        lines.append(second)
        lines.append("其他页面脚本照这个形状，只改编号、路径、输入和「」里的提示。多句提示写成多个字符串，页面文本要包含每一句。")
    lines.extend(_coverage(cfg))
    return "\n".join(lines)


def _coverage(cfg: Config) -> list[str]:
    """示例之后提醒覆盖规格说明书，不规定固定编号清单。"""
    if cfg.channel == "api":
        scope = "本次只写接口用例，不要写页面用例和页面脚本。"
    elif cfg.channel == "ui":
        scope = "本次只写手工用例和对应脚本。每个脚本自己完成步骤。"
    else:
        scope = "规格说明书里的每条需求都要在用例的「对应需求」里出现。页面能验证的写手工用例，接口能验证的写接口用例。"
    lines = [
        "【覆盖】",
        "用例只根据你写的需求规格说明书来写，编号用说明书里的编号。",
        "示例只演示版式。只交示例里的那一条算没写完。",
        scope,
    ]
    if cfg.requirements:
        lines.append("本次用例只覆盖这些需求编号：" + "、".join(cfg.requirements) + "。其余不要写。")
    if cfg.channel != "ui":
        lines.append("接口用例先写表格，再写入文末 json，两边编号一致。按依赖排列：先注册或登录，再查询登录状态，再退出。")
    return lines
