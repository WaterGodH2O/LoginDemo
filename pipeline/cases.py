# 用例解析
#
# 职责：从测试用例文档取出可执行的页面用例和接口用例。
# 输入：AIgen-docs/测试用例.md；requirements、channel；pipeline/work/ui/ 下的脚本。
# 输出：页面用例列表和接口用例列表。解析失败时列表为空，并给出原因。
#
# 本机文档路径：当前目录下 AIgen-docs/测试用例.md。
# 页面脚本：pipeline/work/ui/test_编号.py，编号小写且连字符改为下划线。
# 字段可以写成「通道：ui」，也可以写在 Markdown 表格里，例如「测试方式 | 手工」。
# 编号以 TC-UI 或 TC-API 开头时，没有通道也按页面或接口处理。
# 接口用例优先读文末 JSON。没有 JSON 时，从接口用例的步骤和预期里取方法、路径和状态码。
# 缺字段，或页面用例没有脚本时，不启动浏览器。

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from config import Config

_HEAD = re.compile(r"^#{1,6}\s+(?:用例\s*)?(TC-[A-Za-z0-9-]+)\b")
_FIELD = re.compile(
    r"^(?:[-*+]\s+)?(编号|所属需求|需求编号|需求|通道|步骤|数据|预期原文|预期)\s*[:：]\s*(.*)$"
)
_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|")
_TABLE_LABEL = {
    "对应需求": "requirement",
    "所属需求": "requirement",
    "需求编号": "requirement",
    "需求": "requirement",
    "测试方式": "channel",
    "通道": "channel",
    "步骤": "steps",
    "数据": "data",
    "测试数据": "data",
    "预期结果": "expected",
    "预期原文": "expected",
    "预期": "expected",
}
_CALL = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\s+(/api/[A-Za-z0-9_./-]*)", re.I)
_BODY = re.compile(r"请求体\s*`(\{.*?\})`")
_STATUS = re.compile(r"返回\s*(\d{3})")
_QUOTED = re.compile(r"[「\"]([^」\"]+)[」\"]")
_FENCE = re.compile(r"```(?:json)?[ \t]*\n(.*?)```", re.S | re.I)
_KEYS = ("id", "requirement", "channel", "method", "path", "body", "expected_status", "expected_text")


@dataclass
class UiCase:
    id: str
    requirement: str
    channel: str
    steps: str
    data: str
    expected: str
    script: str


@dataclass
class ApiCase:
    id: str
    requirement: str
    channel: str
    method: str
    path: str
    body: object
    expected_status: int
    expected_text: str


@dataclass
class ParseResult:
    ok: bool
    ui_cases: list[UiCase] = field(default_factory=list)
    api_cases: list[ApiCase] = field(default_factory=list)
    reason: str = ""


def script_filename(case_id: str) -> str:
    return "test_" + case_id.strip().lower().replace("-", "_") + ".py"


def script_name_candidates(case_id: str) -> list[str]:
    """精确文件名优先，其次接受少写 ui/api 的文件名。"""
    exact = script_filename(case_id)
    names = [exact]
    stem = exact[:-3]
    for marker in ("_ui_", "_api_"):
        prefix = "test_tc" + marker
        if stem.startswith(prefix):
            names.append("test_tc_" + stem[len(prefix):] + ".py")
            break
    tail = case_id.strip().lower().replace("-", "_")
    for prefix in ("tc_ui_", "tc_api_", "tc_"):
        if tail.startswith(prefix):
            names.append("test_" + tail[len(prefix):] + ".py")
            break
    unique: list[str] = []
    for name in names:
        if name not in unique:
            unique.append(name)
    return unique


def case_id_from_script(path: str) -> str:
    stem = Path(path).stem
    if stem.lower().startswith("test_"):
        stem = stem[5:]
    return stem.upper().replace("_", "-")


def parse(cfg: Config) -> ParseResult:
    """读测试用例，过滤需求编号和通道，再给页面用例配对脚本。"""
    path = cfg.docs_dir / "测试用例.md"
    if not path.is_file():
        return ParseResult(False, reason="没有测试用例文件")
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []

    payload, body = _split_json(text)
    ui_raw = _ui_blocks(body)
    table_cases, table_problems = _api_from_blocks(ui_raw)
    if payload is None:
        api_cases, api_problems = table_cases, table_problems
        if cfg.channel != "ui" and not api_cases:
            problems.append("缺少可执行的接口用例")
    elif len(table_cases) > len(_api_cases(payload)[0]):
        api_cases, api_problems = table_cases, table_problems
    else:
        api_cases, api_problems = _api_cases(payload)
    problems.extend(api_problems)
    ui_cases, ui_problems = _complete_ui(ui_raw)
    # 只跑接口时，页面用例写得不完整也不挡接口。
    if cfg.channel != "api":
        problems.extend(ui_problems)
    if problems:
        return ParseResult(False, reason="\n".join(problems))

    ui_cases = [item for item in ui_cases if _wanted(item.requirement, item.channel, cfg)]
    api_cases = [item for item in api_cases if _wanted(item.requirement, item.channel, cfg)]
    if cfg.channel != "api":
        missing = _attach_scripts(ui_cases, cfg)
        if missing:
            return ParseResult(False, reason="\n".join(missing))
    else:
        ui_cases = []
    if cfg.channel == "ui":
        api_cases = []
    if cfg.channel == "ui" and not ui_cases:
        return ParseResult(False, reason="没有页面用例")
    if cfg.channel == "api" and not api_cases:
        return ParseResult(False, reason="没有接口用例")
    if cfg.channel == "all" and not ui_cases and not api_cases:
        return ParseResult(False, reason="没有可执行用例")
    return ParseResult(True, ui_cases, api_cases, "")


def _split_json(text: str) -> tuple[list | None, str]:
    found: list | None = None
    span: tuple[int, int] | None = None
    for match in _FENCE.finditer(text):
        raw = match.group(1).strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            value = [value]
        if isinstance(value, list):
            found = value
            span = match.span()
    if span is None:
        return None, text
    body = text[: span[0]] + text[span[1] :]
    return found, body


def _ui_blocks(text: str) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    field_name = ""

    def open_case(case_id: str) -> dict[str, str]:
        return {
            "id": case_id,
            "requirement": "",
            "channel": "",
            "steps": "",
            "data": "",
            "expected": "",
            "_seen": "",
        }

    for line in text.splitlines():
        stripped = line.strip()
        head = _HEAD.match(stripped)
        if head:
            if current:
                cases.append(_seal(current))
            current = open_case(head.group(1))
            field_name = ""
            continue
        row = _ROW.match(stripped)
        if row and current is not None:
            label = row.group(1).strip()
            value = row.group(2).strip()
            if re.fullmatch(r":?-{2,}:?", label):
                continue
            key = _TABLE_LABEL.get(label)
            if key:
                current[key] = _channel(value) or value if key == "channel" else value
                current["_seen"] += key
                field_name = key
            continue
        matched = _FIELD.match(stripped)
        if matched:
            label, value = matched.group(1), matched.group(2).strip()
            if label == "编号":
                if current and current["id"] and current["id"] != value and current["_seen"]:
                    cases.append(_seal(current))
                    current = open_case(value)
                elif current is None:
                    current = open_case(value)
                else:
                    current["id"] = value or current["id"]
                current["_seen"] += "id"
                field_name = "id"
                continue
            if current is None:
                continue
            key = {
                "所属需求": "requirement",
                "需求编号": "requirement",
                "需求": "requirement",
                "通道": "channel",
                "步骤": "steps",
                "数据": "data",
                "预期原文": "expected",
                "预期": "expected",
            }[label]
            current[key] = value
            current["_seen"] += key
            field_name = key
            continue
        if stripped.startswith("#"):
            field_name = ""
            continue
        if current and field_name in {"steps", "data", "expected", "requirement"} and stripped:
            current[field_name] = (current[field_name] + "\n" + stripped).strip()
    if current:
        cases.append(_seal(current))
    return cases


def _seal(current: dict[str, str]) -> dict[str, str]:
    if not _channel(current.get("channel", "")):
        case_id = current.get("id", "").upper()
        if case_id.startswith("TC-UI"):
            current["channel"] = "ui"
        elif case_id.startswith("TC-API"):
            current["channel"] = "api"
    return current


def _complete_ui(raw_cases: list[dict[str, str]]) -> tuple[list[UiCase], list[str]]:
    problems: list[str] = []
    done: list[UiCase] = []
    seen: set[str] = set()
    for raw in raw_cases:
        case_id = raw.get("id", "").strip()
        if not case_id:
            continue
        channel = _channel(raw.get("channel", ""))
        if channel == "api":
            continue
        if channel != "ui":
            problems.append(f"{case_id} 缺少通道")
            continue
        requirement = raw.get("requirement", "").strip()
        steps = raw.get("steps", "").strip()
        data = raw.get("data", "").strip() or steps
        expected = raw.get("expected", "").strip()
        blank = [
            name
            for name, value in (
                ("所属需求", requirement),
                ("步骤", steps),
                ("预期", expected),
            )
            if not value
        ]
        if blank:
            problems.append(f"{case_id} 缺少" + "、".join(blank))
            continue
        if case_id in seen:
            problems.append(f"编号重复：{case_id}")
            continue
        seen.add(case_id)
        done.append(UiCase(case_id, requirement, "ui", steps, data, expected, ""))
    return done, problems


def _api_cases(payload: list) -> tuple[list[ApiCase], list[str]]:
    cases: list[ApiCase] = []
    problems: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            problems.append(f"第 {index} 条接口用例不是对象")
            continue
        missing = [key for key in _KEYS if key not in item]
        if missing:
            problems.append(f"第 {index} 条接口用例缺少字段：" + "、".join(missing))
            continue
        channel = _channel(str(item.get("channel", "")))
        if channel == "ui":
            continue
        if channel != "api":
            problems.append(f"第 {index} 条接口用例通道无效")
            continue
        case_id = item.get("id")
        requirement = item.get("requirement")
        method = item.get("method")
        path = item.get("path")
        expected_text = item.get("expected_text")
        status = item.get("expected_status")
        if not all(isinstance(value, str) and value.strip() for value in (case_id, requirement, method, path)):
            problems.append(f"第 {index} 条接口用例有空字段")
            continue
        if not isinstance(expected_text, str):
            problems.append(f"{case_id} 的 expected_text 不是字符串")
            continue
        if isinstance(status, bool) or not isinstance(status, int):
            problems.append(f"{case_id} 的 expected_status 不是整数")
            continue
        if case_id in seen:
            problems.append(f"编号重复：{case_id}")
            continue
        seen.add(case_id)
        route = path if path.startswith("/") else "/" + path
        cases.append(
            ApiCase(
                case_id.strip(),
                requirement.strip(),
                "api",
                method.strip().upper(),
                route,
                item.get("body"),
                status,
                expected_text,
            )
        )
    return cases, problems


def _attach_scripts(ui_cases: list[UiCase], cfg: Config) -> list[str]:
    problems: list[str] = []
    ui_dir = cfg.ui_dir
    available = set(path.name for path in ui_dir.glob("*.py")) if ui_dir.is_dir() else set()
    pending = list(ui_cases)
    for rank in range(3):
        still: list[UiCase] = []
        for case in pending:
            candidates = script_name_candidates(case.id)
            if rank >= len(candidates):
                still.append(case)
                continue
            name = candidates[rank]
            if name in available:
                available.remove(name)
                case.script = f"{cfg.work_dir}/ui/{name}"
                continue
            still.append(case)
        pending = still
    for case in pending:
        expected = script_name_candidates(case.id)[0]
        hint = " ".join(case.expected.split())
        if len(hint) > 80:
            hint = hint[:80] + "…"
        problems.append(f"{case.id} 没有对应脚本 {cfg.work_dir}/ui/{expected}。该文件的 Python 字符串要包含预期：{hint}")
    return problems


def _wanted(requirement: str, channel: str, cfg: Config) -> bool:
    if cfg.channel != "all" and channel != cfg.channel:
        return False
    if not cfg.requirements:
        return True
    text = requirement.strip()
    parts = re.split(r"[\s,，、]+", text)
    return any(item in parts for item in cfg.requirements)


def _api_from_blocks(raw_cases: list[dict[str, str]]) -> tuple[list[ApiCase], list[str]]:
    """从表格或字段行里的接口用例取出一次请求。"""
    cases: list[ApiCase] = []
    problems: list[str] = []
    seen: set[str] = set()
    for raw in raw_cases:
        if _channel(raw.get("channel", "")) != "api":
            continue
        case_id = raw.get("id", "").strip()
        requirement = raw.get("requirement", "").strip()
        steps = raw.get("steps", "").strip()
        expected = raw.get("expected", "").strip()
        if not case_id:
            continue
        call = _CALL.search(steps)
        if call is None:
            problems.append(f"{case_id} 的步骤里没有接口路径")
            continue
        method, path = call.group(1).upper(), call.group(2)
        body: object = None
        body_match = _BODY.search(steps)
        if body_match:
            try:
                body = json.loads(body_match.group(1))
            except json.JSONDecodeError:
                problems.append(f"{case_id} 的请求体不是 JSON")
                continue
        first = expected.split("第 2 步", 1)[0]
        status = _expected_status(first)
        text = _expected_phrase(first)
        if status is None:
            problems.append(f"{case_id} 的预期里没有 HTTP 状态码")
            continue
        if not text:
            problems.append(f"{case_id} 的预期里没有可核对的提示")
            continue
        if not requirement:
            problems.append(f"{case_id} 缺少所属需求")
            continue
        if case_id in seen:
            problems.append(f"编号重复：{case_id}")
            continue
        seen.add(case_id)
        cases.append(ApiCase(case_id, requirement, "api", method, path, body, status, text))
    return cases, problems


def _expected_status(expected: str) -> int | None:
    match = _STATUS.search(expected)
    if match:
        return int(match.group(1))
    return None


def _expected_phrase(expected: str) -> str:
    quoted = _QUOTED.search(expected)
    if quoted:
        return quoted.group(1).strip()
    return " ".join(expected.split())


def _channel(value: str) -> str:
    text = value.strip().lower()
    if text in {"ui", "页面", "page", "手工"} or "手工" in value or "页面" in value:
        return "ui"
    if text in {"api", "接口"} or "接口" in value:
        return "api"
    return ""
