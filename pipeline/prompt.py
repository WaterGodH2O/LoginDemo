# 消息拼装
#
# 职责：把文件列表拼成一条用户消息。使用普通文本，不走文件上传接口。
# 输入：文件列表；requirements、channel；失败后的重发原因。
# 输出：一条用户消息。后续轮的执行结果由结果消息模块另拼，这里不再附带源码。
#
# 本机默认通道 all，需求编号默认不限制。
# 页面脚本目录 pipeline/work/ui/，文档目录 AIgen-docs/。
# 前端 http://localhost:5173，后端 http://localhost:5000。
# 任务说明末尾附上已有测试用例原文，只作版式示例。

from __future__ import annotations

from pathlib import Path

from cases import LENGTH_RULES
from collect import SourceFile
from config import Config
from doc_examples import TESTCASES

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
    parts.append(_task(cfg))
    return "\n".join(parts).rstrip() + "\n"


def fix_message(reason: str) -> str:
    """检查或切分未通过时，交回原因，要求只重发用例和页面脚本。"""
    lines = [
        "上一次输出不能用。请只重发测试用例和页面脚本。",
        "不要写测试执行记录、测试报告或 Bug 单。",
        "断言使用用例里的预期原文。预期含「用户名长度不足」时，不要改成断言「注册成功」。",
        "不要跳过测试。分隔行格式：===== 相对路径 =====",
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


def _task(cfg: Config) -> str:
    rules = "；".join(LENGTH_RULES)
    lines = [
        "请根据 PRD 和源码生成测试用例，并为每条页面用例生成 Playwright Python 脚本。",
        "页面用例的断言必须使用 PRD 中的预期原文。",
        "接口用例写入测试用例末尾的 JSON，不要写成 Playwright。",
        "这一步不输出测试执行记录、测试报告和 Bug 单。",
        "回复按分隔行切分，路径写在等号中间，例如：",
        "===== AIgen-docs/测试用例.md =====",
        f"===== {cfg.work_dir}/ui/test_tc_ui_reg_002.py =====",
        "用例正文使用这些字段：编号、所属需求、通道（ui 或 api）、步骤、数据、预期。",
        "字段独占一行，写成「编号：TC-UI-REG-002」。一条用例一个二级标题，标题里带编号。",
        f"长度规则至少包含：{rules}。",
        "文件末尾放一个 json 代码块。接口用例字段为 id、requirement、channel、method、path、body、expected_status、expected_text。",
        "页面脚本使用 Playwright 同步 API。退出码 0 表示页面出现预期文案，退出码 1 表示没有。",
        f"从环境变量 WEB_BASE 读取前端地址，缺省 {cfg.web_base}。HEADED 为 1 时浏览器可见，否则无头。",
        f"失败截图写到 {cfg.work_dir}/screenshots/用例编号.png。",
        "每个页面用例一个 py 文件，文件名为 test_ 加编号小写，连字符换成下划线。",
        "脚本必须能被 Python 编译。断言包含该用例的预期原文。不要跳过测试。",
        "预期为用户名长度不足的用例，不要改成断言注册成功。",
        "不要修改产品代码，不要写 frontend/ 或 backend/ 下的文件。",
    ]
    if cfg.requirements:
        lines.append("只处理这些需求编号：" + "、".join(cfg.requirements))
    if cfg.channel == "api":
        lines.append("通道范围：只写接口用例。")
    elif cfg.channel == "ui":
        lines.append("通道范围：只写页面用例。页面脚本仍要给出。")
    lines.extend(
        [
            "下面是仓库里已有的测试用例，只作章节、表格和措辞示例。",
            "生成结果仍须满足上面的字段行、长度规则原文、文末 JSON 和分隔行。",
            "不要把文件写到 docs/ 下的原路径，也不要照抄示例里的账号和日期。",
            "【示例：测试用例】",
            TESTCASES.strip(),
        ]
    )
    return "\n".join(lines)
