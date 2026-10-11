# 测试流水线
#
# 本地 Python 脚本。把工程目录、前后端代码和项目文档打包成对话文本，交给大模型。
# 模型先写出测试用例和 Playwright 脚本。脚本再启动前后端并执行。
# 执行结果送回模型。模型继续写脚本以定位缺陷，或直接写出执行记录、测试报告和 Bug 单。
#
# 不做成浏览器插件或编辑器扩展。
# 脚本不修改 frontend/ 和 backend/，也不补上用户名长度校验。
# 预期以 PRD 为准。源码里没有长度校验，不能据此把预期改成注册成功。
#
# 入口：在仓库根目录执行
# python pipeline/run.py --source frontend --source backend
# 必须传入完整的项目前后端代码。PRD 使用默认路径时可以不传 --prd，文件缺失则停止。
# 大模型密钥用环境变量提供，不放进命令行。


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
#    请根据 PRD 和源码生成测试用例，并为每条页面用例生成 Playwright Python 脚本。
#    页面用例的断言必须使用 PRD 中的预期原文。
#    接口用例写入测试用例末尾的 JSON，不要写成 Playwright。
#
# 2. 模型第一次输出
#    此时还没有运行结果，模型只输出测试用例和页面脚本。
#    不在这一步输出测试执行记录、测试报告或 Bug 单。
#
#    回复用分隔行标出每个文件，便于脚本切分落盘：
#
#    ===== docs/testcases/测试用例.md =====
#    ...Markdown...
#    ===== pipeline/work/ui/test_tc_ui_reg_002.py =====
#    ...Playwright Python...
#
#    测试用例.md 记录编号、所属需求、通道（ui 或 api）、步骤、数据和预期原文。
#    长度规则至少包含「去掉首尾空格后不足 6 位应拒绝」和「刚好 6 位可以注册」。
#    文件末尾附一个 json 代码块，供脚本执行接口用例，字段为：
#    id、requirement、channel、method、path、body、expected_status、expected_text。
#
#    页面用例每个文件对应一条用例，使用 Playwright 同步 Python API。
#    写盘前检查：脚本能被 Python 编译；断言包含该用例的预期原文；
#    不包含跳过测试，也不把失败用例改成断言「注册成功」。
#    检查不通过则把原因交回模型重新生成，次数见 --codegen-retries。
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
#    请只做一件事：继续写 Playwright 脚本以缩小失败位置，或给出最终文档。
#    继续定位时，断言仍使用上面的预期原文。
#    回复的第一行只能是「决定：继续定位」或「决定：输出结论」。
#
# 4. 模型根据反馈继续
#    第一行是「决定：继续定位」时，后面只给新的 Playwright 文件，格式同第 2 步的分隔行。
#    脚本检查并执行后，把新的【执行结果】再送回模型。
#    定位轮数不超过 --locate-rounds。用尽后，下一轮只允许「决定：输出结论」。
#
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
# --locate-rounds     默认 2
#                     第 4 步「决定：继续定位」的最多轮数。用尽后只接受「决定：输出结论」。
# --timeout           默认 30
#                     单次 HTTP 请求或单条页面用例的超时秒数。
# --headed            默认关闭
#                     加上后显示浏览器窗口。
# --work-dir          默认 pipeline/work
#                     Playwright 脚本、截图和本轮执行结果。
# --dry-run           默认关闭
#                     只做到第 2 步并落盘测试用例和页面脚本，不启动 Demo，不写后三份文档。


# 环境变量
#
# LLM_API_KEY
# 调用大模型时必须。接口密钥。
# 密钥只从环境变量读取。不要写入脚本、命令行或仓库。


# 产出
#
# docs/testcases/测试用例.md                         第 2 步，模型生成
# pipeline/work/ui/*.py                              第 2 步和第 4 步，Playwright 脚本
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
    files = collect.collect(cfg)
    messages = [
        llm.system_message(),
        {"role": "user", "content": prompt.first_message(files, cfg)},
    ]
    parsed = _generate_cases(cfg, messages)
    if cfg.dry_run:
        print(f"已写入 {cfg.docs_dir / '测试用例.md'}")
        return 0
    if parsed.ui_cases:
        ui_run.prepare_playwright()
    servers.check_runtime(cfg)
    servers.ensure(cfg)
    ui_results = ui_run.run(parsed.ui_cases, cfg)
    api_results = api_run.run(parsed.api_cases, cfg)
    return _follow_up(cfg, messages, parsed, ui_results, api_results)


def _generate_cases(cfg: config.Config, messages: list[dict[str, str]]) -> cases.ParseResult:
    """反复请模型给出用例和页面脚本，直到检查通过或次数用尽。"""
    left = cfg.codegen_retries
    while True:
        reply = llm.complete(cfg, messages)
        messages.append({"role": "assistant", "content": reply})
        written = split.apply(reply, "first", cfg)
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
        if left <= 0:
            raise PipelineError(reason or "页面脚本检查未通过")
        messages.append({"role": "user", "content": prompt.fix_message(reason)})
        left -= 1


def _follow_up(
    cfg: config.Config,
    messages: list[dict[str, str]],
    parsed: cases.ParseResult,
    ui_results: list[ui_run.UiResult],
    api_results: list[api_run.ApiResult],
) -> int:
    """把执行结果送回模型，按决定继续定位或写出三份文档。"""
    used = 0
    left = cfg.codegen_retries
    while True:
        passed = _all_passed(ui_results, api_results)
        force = passed or used >= cfg.locate_rounds
        reason = "" if passed or used < cfg.locate_rounds else "定位轮数已用尽，只接受「决定：输出结论」"
        messages.append(
            {
                "role": "user",
                "content": feedback.build(ui_results, api_results, cfg, force, reason),
            }
        )
        reply = llm.complete(cfg, messages)
        messages.append({"role": "assistant", "content": reply})
        decision = loop.parse_decision(reply, passed, used, cfg.locate_rounds)
        if decision.action == "invalid":
            if left <= 0:
                raise PipelineError(decision.message)
            messages.append({"role": "user", "content": prompt.fix_message(decision.message)})
            left -= 1
            continue
        if decision.action == "locate":
            located = split.apply(reply, "locate", cfg)
            if not located.ok:
                if left <= 0:
                    raise PipelineError(located.reason)
                messages.append({"role": "user", "content": prompt.fix_message(located.reason)})
                left -= 1
                continue
            rerun = _cases_for_scripts(parsed.ui_cases, located.written)
            checked = check_script.check(rerun, cfg, left)
            if not checked.ok:
                if left <= 0:
                    raise PipelineError(checked.reason)
                messages.append({"role": "user", "content": prompt.fix_message(checked.reason)})
                left -= 1
                continue
            fresh = ui_run.run(rerun, cfg)
            ui_results = _replace_ui(ui_results, fresh)
            used += 1
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
            messages.append({"role": "user", "content": prompt.fix_message(gap or concluded.reason)})
            left -= 1
            continue
        for path in concluded.written:
            print(path)
        return 0


def _cases_for_scripts(ui_cases: list[cases.UiCase], written: list[str]) -> list[cases.UiCase]:
    names = {path.rsplit("/", 1)[-1] for path in written}
    return [case for case in ui_cases if case.script.rsplit("/", 1)[-1] in names]


def _replace_ui(
    previous: list[ui_run.UiResult],
    fresh: list[ui_run.UiResult],
) -> list[ui_run.UiResult]:
    by_id = {item.case_id: item for item in previous}
    for item in fresh:
        by_id[item.case_id] = item
    return list(by_id.values())


def _all_passed(ui_results: list[ui_run.UiResult], api_results: list[api_run.ApiResult]) -> bool:
    return all(item.passed for item in ui_results) and all(item.passed for item in api_results)


if __name__ == "__main__":
    sys.exit(main())

