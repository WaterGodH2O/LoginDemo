# 测试流水线
#
# 本地 Python 脚本。把工程目录、前后端代码和项目文档打包成对话文本，交给大模型。
# 模型先根据 PRD 写出需求规格说明书，再根据该说明书写测试用例和 Playwright 脚本。
# 脚本再启动前后端并执行。执行结果送回模型，由模型写出执行记录、测试报告和 Bug 单。
#
# 不做成浏览器插件或编辑器扩展。
# 脚本不修改 frontend/ 和 backend/，也不补上用户名长度校验。
# 预期以 PRD 为准。源码里没有长度校验，不能据此把预期改成注册成功。
#
# 入口：在仓库根目录执行
# python pipeline/run.py --source frontend --source backend
# 必须传入完整的项目前后端代码。PRD 使用默认路径时可以不传 --prd，文件缺失则停止。
# 大模型密钥用环境变量提供，不放进命令行。
# 读入源码之前先发一条测试对话，确认密钥和模型可用。
# 探测和后续对话覆盖写入工作目录 dialogue.log，不写密钥。


# 全链路
#
# 1. 打包输入
#    脚本在本地读取文件，拼成一条用户消息，不做单独的文件通道。
#    必选：前后端源码目录，以及 PRD。
#    可选：其他项目文档，由 --docs 指定。不默认读入已有测试报告和已有 Bug 单，避免模型照抄结论。
#    不读取依赖目录、构建产物、锁文件、缓存和数据库文件。
#       例如 node_modules/、dist/、package-lock.json、__pycache__/、*.db、.git/、pipeline/work/。
#
#    消息格式如下。路径写在代码块外面。任务写在所有文件之后。
#    文件原文若包含三个反引号，该文件改用 <file path="..."> 与 </file> 包裹。
#
#    【目录】
#    frontend/
#      src/pages/Register.jsx
#      src/api.js
#    backend/
#      app.py
#    docs/prd/登录注册Demo-PRD.md
#
#    【文件 frontend/src/pages/Register.jsx】
#    ```jsx
#    ...文件原文...
#    ```
#
#    【文件 backend/app.py】
#    ```python
#    ...文件原文...
#    ```
#
#    【文件 docs/prd/登录注册Demo-PRD.md】
#    ```markdown
#    ...文件原文...
#    ```
#
#    请根据 PRD 生成需求规格说明书。通过后再根据该说明书写测试用例和 Playwright 脚本。
#    「」里只放页面短提示。脚本字符串写入该用例的这些短提示，不要写成别的编号。
#    接口用例只写在测试用例文件末尾的 JSON，不要写成 Playwright，也不要插在用例中间。
#
# 2. 模型先写需求规格说明书，再写测试用例和页面脚本
#    第一轮只输出需求规格说明书，格式对齐 docs/srs/登录注册Demo-需求规格说明书.md。
#    落盘到 AIgen-docs/需求规格说明书.md。缺编号或字段时交回重写。
#    第二轮把这份说明书送回模型，只输出测试用例和页面脚本。
#    不在这一步输出测试执行记录、测试报告或 Bug 单。
#    先写完测试用例，再写完全部页面脚本，然后结束。
#
#    回复用分隔行标出每个文件，便于脚本切分落盘：
#
#    ===== AIgen-docs/需求规格说明书.md =====
#    ...每条需求一个四级标题和字段表格...
#    ===== AIgen-docs/测试用例.md =====
#    ...表格对齐 docs/testcases，json 代码块在该文件最后...
#    ===== pipeline/work/ui/test_tc_ui_reg_002.py =====
#    ...该文件的字符串是「用户名长度不足」，不是「请输入用户名」或「注册成功」...
#
#    测试用例.md 用表格记录对应需求、测试方式（手工或接口）、步骤和预期。
#    文件末尾一个 json 代码块，字段为：
#    id、requirement、channel、method、path、body、expected_status、expected_text。
#
#    每个页面用例恰好一个脚本。文件名为 test_ 加编号小写，连字符改下划线。
#    写盘前检查：脚本能被 Python 编译；字符串包含该用例「」中的提示原文；
#    不包含跳过测试。检查不通过则把原因交回模型重新生成，次数见 --codegen-retries。
#
# 3. 启动系统并执行
#    账号服务未监听 --api-base 时，脚本启动 python backend/app.py（默认端口 5000）。
#    前端未监听 --web-base 时，脚本在 frontend/ 执行 npm run dev（默认端口 5173）。
#    已在监听则直接复用，不重复启动。
#
#    页面用例使用 Playwright 同步 Python API。
#    在仓库根目录用子进程运行脚本，并同时取标准输出和退出码。
#    示例见 pipeline/example/register_short_username.py，运行方式：
#      python pipeline/example/register_short_username.py
#    标准输出是【执行结果】文本，包含用例、预期、实际、地址和截图路径。
#    退出码 0 表示页面出现预期文案，退出码 1 表示没有出现。
#    PowerShell 用 $LASTEXITCODE 读取退出码。
#    示例截图写在 pipeline/example/last-result.png。
#    流水线生成的脚本放在 pipeline/work/ui/，失败截图放在 pipeline/work/screenshots/。
#    按当前预埋缺陷，不足 6 位的用户名会注册成功，该示例的退出码应为 1，
#    实际文案为「注册成功，请登录」。
#
#    接口用例：脚本按测试用例末尾的 JSON 发送 HTTP 请求，不生成 Playwright。
#    通过与否以进程退出码和 HTTP 比较结果为准，不请模型在运行前判断。
#
#    结果拼成下一条用户消息。第二轮起不再重复粘贴全部源码，只送本轮失败项：
#
#    【执行结果】
#    用例：TC-UI-REG-002
#    需求：REQ-REG-002
#    脚本：pipeline/work/ui/test_tc_ui_reg_002.py
#    结果：失败
#    预期：用户名长度不足
#    实际：页面出现「注册成功，请登录」，地址变为 /login
#    退出码：1
#    截图：pipeline/work/screenshots/TC-UI-REG-002.png
#    输出摘录：
#    ...pytest 或 HTTP 响应原文，过长则截断...
#
#    每个页面用例只执行一次。回复的第一行只能是「决定：输出结论」。
#    不要再写 Playwright，也不要继续定位。
#
# 4. 模型根据这一次执行结果直接写结论
#    第一行是「决定：输出结论」时，后面按分隔行给出三份文档，脚本落盘：
#
#    ===== docs/test-records/测试执行记录.md =====
#    ===== docs/test-reports/测试报告.md =====
#    ===== docs/bugs/BUG-编号-标题.md =====
#
#    测试执行记录按用例写下步骤、预期、实际和通过或失败。
#    测试报告包含环境、用例统计、失败说明和结论。
#    同一需求的页面失败和接口失败合并为一张 Bug 单。
#    Bug 单包含编号、标题、严重程度、所属需求、关联用例、复现步骤、预期结果、实际结果。
#    实际结果必须来自第 3 步送回的执行结果，不凭源码猜测。
#
#    这些输出不覆盖手工文档：
#    docs/testcases/登录注册Demo-测试用例.md
#    docs/test-records/登录注册Demo-测试执行记录.md
#    docs/test-reports/登录注册Demo-测试报告.md
#    docs/bugs/BUG-001-用户名长度不足仍可注册.md


# 必选输入
#
# 缺失则程序停止，并说明缺少哪一项。
#
# --source            完整的项目前后端代码目录，可重复传入。
#                     须同时包含前端目录和后端目录，例如 frontend 与 backend。
#                     无默认值。
#                     前端读取页面、路由和接口调用，包括注册、登录、首页的表单标签、按钮文案和请求地址。
#                     后端读取路由、请求体、响应文案和存储方式，用来确定接口路径和字段。
#                     脚本只读这些目录，不修改其中的文件。
#
# --prd               默认 docs/prd/登录注册Demo-PRD.md
#                     PRD 文件路径。参数可省略，但该文件必须存在并进入第 1 步的用户消息。
#                     用例预期以这份文档为准。
#
#
# 可选输入
#
# 全部可选。省略时使用默认值。
#
# --docs              默认无，可重复传入
#                     其他项目文档，例如需求规格说明书。
#                     指定后以与源码相同的【文件】格式追加到第 1 步消息。
#                     不要把已有测试报告和已有 Bug 单放进来。
# --web-base          默认 http://localhost:5173
#                     前端地址。页面脚本打开此地址。未监听时在 frontend/ 启动 npm run dev。
# --api-base          默认 http://localhost:5000
#                     账号服务地址。未监听时启动 python backend/app.py。
# --req               默认无，可重复传入
#                     只处理列出的需求编号。省略则处理 PRD 中的全部需求。
# --channel           默认 all
#                     api 只跑接口，ui 只跑页面，all 两者都跑。
# --llm-base-url      默认 https://api.openai.com/v1
#                     大模型接口地址，兼容 OpenAI 的均可。消息使用 messages 数组。
# --llm-model         默认 gpt-4o-mini
#                     模型名称。
# --codegen-retries   默认 3
#                     页面脚本未通过写盘前检查时，交回模型重新生成的次数。
# --locate-rounds     默认 7
#                     保留参数。页面脚本现在每个用例只执行一次，不再按这个轮数重跑。
# --timeout           默认 120
#                     单次 HTTP 请求或单条页面用例的超时秒数。
# --max-tokens        默认 16384
#                     单次模型回复的最大 token 数。不能超过所用模型的输出上限。
# --headed            默认关闭
#                     加上后显示浏览器窗口。
# --work-dir          默认 pipeline/work
#                     Playwright 脚本、截图和本轮执行结果。
# --dry-run           默认关闭
#                     只做到规格说明书和测试用例落盘，不启动 Demo，不写后三份文档。
# --verbose           默认关闭
#                     只控制终端：回显发给模型的消息，并按文件回显模型回复的用例、脚本和结论文档。
#                     对话日志不依赖本开关，默认覆盖写入工作目录 dialogue.log。


# 环境变量
#
# LLM_API_KEY
# 调用大模型时必须。接口密钥。
# 密钥只从环境变量读取。不要写入脚本、命令行或仓库。


# 产出
#
# AIgen-docs/需求规格说明书.md                       第 2 步，模型根据 PRD 生成
# AIgen-docs/测试用例.md                             第 2 步，模型根据规格说明书生成
# pipeline/work/ui/*.py                              第 2 步和第 4 步，Playwright 脚本
# pipeline/work/dialogue.log                         每次运行覆盖，探测、用户消息和模型回复
# pipeline/work/screenshots/                         第 3 步，失败截图
# docs/test-records/测试执行记录.md                  第 4 步，决定输出结论时
# docs/test-reports/测试报告.md                      第 4 步，决定输出结论时
# docs/bugs/BUG-编号-标题.md                         第 4 步，失败需求各一张
#
# pipeline/work/ 不纳入版本库。docs/ 下的新文件由人决定是否提交。


# 判定
#
# 预期结果来自 PRD 和测试用例中的原文。
# REQ-REG-002 的预期保持为拒绝注册并提示用户名长度不足。
# 页面或接口接受了不足 6 位的用户名时，该用例记为失败。
# 定位脚本只用于缩小复现步骤，不修改这条预期。
# 大模型不修改产品代码，也不把失败断言改成与当前页面行为一致。

from __future__ import annotations

import sys

import api_run
import cases
import check_script
import collect
import config
import feedback
import llm
import loop
import prompt
import servers
import split
import ui_run
from config import PipelineError


def main(argv: list[str] | None = None) -> int:
    try:
        cfg = config.load(argv)
        return _run(cfg)
    except PipelineError as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code


def _run(cfg: config.Config) -> int:
    llm.reset_dialogue_log(cfg)
    llm.probe(cfg)
    files = collect.collect(cfg)
    first = prompt.first_message(files, cfg)
    _echo_to_model(cfg, "规格说明书", first)
    messages = [
        llm.system_message(),
        {"role": "user", "content": first},
    ]
    _generate_srs(cfg, messages)
    srs_text = (cfg.repo_root / loop.SRS_REL).read_text(encoding="utf-8")
    _user(cfg, messages, "用例任务", prompt.cases_message(cfg, srs_text))
    parsed = _generate_cases(cfg, messages)
    if cfg.dry_run:
        print(f"已写入 {cfg.docs_dir / '需求规格说明书.md'}")
        print(f"已写入 {cfg.docs_dir / '测试用例.md'}")
        return 0
    if parsed.ui_cases:
        ui_run.prepare_playwright()
    servers.check_runtime(cfg)
    servers.ensure(cfg)
    ui_results = ui_run.run(parsed.ui_cases, cfg)
    api_results = api_run.run(parsed.api_cases, cfg)
    return _follow_up(cfg, messages, parsed, ui_results, api_results)


def _generate_srs(cfg: config.Config, messages: list[dict[str, str]]) -> str:
    """请模型根据 PRD 写出需求规格说明书，直到检查通过或次数用尽。"""
    left = cfg.codegen_retries
    bonus = 4
    previous_issues: int | None = None
    while True:
        reply = llm.complete(cfg, messages)
        _echo_reply(cfg, reply)
        messages.append({"role": "assistant", "content": reply})
        written = split.apply(reply, "srs", cfg)
        path = cfg.docs_dir / "需求规格说明书.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        reason = written.reason
        if written.ok:
            if text.strip():
                return text
            reason = "需求规格说明书是空文件"
        issues = _issue_count(reason)
        improved = previous_issues is not None and issues < previous_issues
        previous_issues = issues
        if improved and bonus > 0:
            bonus -= 1
        else:
            if left <= 0:
                raise PipelineError(reason or "需求规格说明书未通过")
            left -= 1
        print(reason, flush=True)
        _user(cfg, messages, "重发原因", prompt.srs_fix_message(reason))


def _generate_cases(cfg: config.Config, messages: list[dict[str, str]]) -> cases.ParseResult:
    """反复请模型给出用例和页面脚本，直到检查通过或次数用尽。"""
    _clear_ui_scripts(cfg)
    left = cfg.codegen_retries
    bonus = 4
    previous_issues: int | None = None
    have_cases = False
    while True:
        reply = llm.complete(cfg, messages)
        _echo_reply(cfg, reply)
        messages.append({"role": "assistant", "content": reply})
        written = split.apply(reply, "first", cfg, keep_cases=have_cases)
        if f"{config.DOCS_DIR}/测试用例.md" in written.written:
            have_cases = True
        reason = written.reason
        parsed = cases.parse(cfg) if written.ok else None
        if written.ok and parsed is not None and not parsed.ok:
            reason = parsed.reason
        checked = None
        if written.ok and parsed is not None and parsed.ok:
            checked = check_script.check(parsed.ui_cases, cfg, left)
            if not checked.ok:
                reason = checked.reason
        if written.ok and parsed is not None and parsed.ok and checked is not None and checked.ok:
            return parsed
        issues = _issue_count(reason)
        improved = previous_issues is not None and issues < previous_issues
        previous_issues = issues
        if improved and bonus > 0:
            bonus -= 1
        else:
            if left <= 0:
                raise PipelineError(reason or "页面脚本检查未通过")
            left -= 1
        print(reason, flush=True)
        script_gap = parsed is not None and not parsed.ok and _only_missing_scripts(parsed.reason)
        assertion_gap = parsed is not None and parsed.ok and checked is not None and not checked.ok
        scripts_only = bool(have_cases and (script_gap or assertion_gap))
        _user(cfg, messages, "重发原因", prompt.fix_message(reason, scripts_only=scripts_only))


def _issue_count(reason: str) -> int:
    lines = [line.strip() for line in (reason or "").splitlines() if line.strip()]
    return sum(1 for line in lines if not line.startswith("剩余重试次数"))


def _only_missing_scripts(reason: str) -> bool:
    lines = [line.strip() for line in (reason or "").splitlines() if line.strip()]
    return bool(lines) and all("没有对应脚本" in line for line in lines)


def _clear_ui_scripts(cfg: config.Config) -> None:
    """新一轮生成前清掉旧页面脚本，避免编号对上过期文件。"""
    ui = cfg.ui_dir
    if not ui.is_dir():
        return
    for path in ui.glob("*.py"):
        path.unlink()


def _follow_up(
    cfg: config.Config,
    messages: list[dict[str, str]],
    parsed: cases.ParseResult,
    ui_results: list[ui_run.UiResult],
    api_results: list[api_run.ApiResult],
) -> int:
    """把一次执行结果送回模型，只写结论文档，不再重跑页面脚本。"""
    del parsed
    left = cfg.codegen_retries
    passed = _all_passed(ui_results, api_results)
    while True:
        _user(
            cfg,
            messages,
            "执行结果",
            feedback.build(
                ui_results,
                api_results,
                cfg,
                True,
                (
                    "全部用例已通过。每个页面用例只执行一次。不要再写 Playwright 脚本。请直接输出结论。"
                    if passed
                    else "每个页面用例只执行一次。不要再写 Playwright 脚本。请根据上面的执行结果直接输出结论。"
                ),
            ),
        )
        reply = llm.complete(cfg, messages)
        _echo_reply(cfg, reply)
        messages.append({"role": "assistant", "content": reply})
        decision = loop.parse_decision(reply, passed, 0, cfg.locate_rounds, allow_locate=False)
        if decision.action != "conclude":
            if left <= 0:
                raise PipelineError(decision.message or "只接受「决定：输出结论」")
            _user(cfg, messages, "重发原因", prompt.decision_fix_message(decision.message))
            left -= 1
            continue
        concluded = split.apply(reply, "conclude", cfg)
        gap = loop.conclusion_gap(
            cfg.repo_root,
            concluded.written,
            cfg.web_base,
            cfg.api_base,
            had_failures=not passed,
        )
        if not concluded.ok or gap:
            if left <= 0:
                raise PipelineError(gap or concluded.reason)
            print(gap or concluded.reason, flush=True)
            _user(cfg, messages, "重发原因", prompt.conclusion_fix_message(gap or concluded.reason))
            left -= 1
            continue
        for path in concluded.written:
            print(path)
        return 0


def _echo_to_model(cfg: config.Config, title: str, text: str) -> None:
    llm.write_dialogue(cfg, f"发给模型：{title}", text)
    if not cfg.verbose:
        return
    print(f"======== 发给模型：{title} ========", flush=True)
    body = (text or "").rstrip()
    print(body if body else "（空消息）", flush=True)
    print("======== 发送结束 ========", flush=True)
    print(flush=True)


def _user(cfg: config.Config, messages: list[dict[str, str]], title: str, content: str) -> None:
    _echo_to_model(cfg, title, content)
    messages.append({"role": "user", "content": content})


def _echo_reply(cfg: config.Config, reply: str) -> None:
    llm.write_dialogue(cfg, "模型回复", reply)
    if cfg.verbose:
        split.echo(reply)


def _all_passed(ui_results: list[ui_run.UiResult], api_results: list[api_run.ApiResult]) -> bool:
    return all(item.passed for item in ui_results) and all(item.passed for item in api_results)


if __name__ == "__main__":
    sys.exit(main())

