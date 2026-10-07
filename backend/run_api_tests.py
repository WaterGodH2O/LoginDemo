"""按测试用例执行接口测试，并在终端打印结果。"""

import json
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

BASE = "http://127.0.0.1:5000"
BACKEND = Path(__file__).resolve().parent
DB_PATH = BACKEND / "app.db"
PYTHON = BACKEND / ".venv" / "Scripts" / "python.exe"
FIXTURE_USERS = ("abcde", "apireg", "spaces")


def opener():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def call(client, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if body is not None else {}
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with client.open(request, timeout=10) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        raw = error.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return error.code, payload


def describe(status, payload):
    return f"HTTP {status}，{json.dumps(payload, ensure_ascii=False)}"


def clean_fixtures():
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        f"DELETE FROM users WHERE username IN ({','.join('?' for _ in FIXTURE_USERS)})",
        FIXTURE_USERS,
    )
    connection.commit()
    connection.close()


def message_is(payload, text):
    return payload.get("message") == text


def no_session(client):
    status, payload = call(client, "GET", "/api/me")
    return status == 401 and message_is(payload, "未登录")


def test_reg_001():
    status, payload = call(opener(), "POST", "/api/register", {"username": "", "password": "Pass1234"})
    ok = status == 400 and message_is(payload, "请输入用户名")
    return ok, describe(status, payload)


def test_reg_002():
    status, payload = call(opener(), "POST", "/api/register", {"username": "   ", "password": "Pass1234"})
    ok = status == 400 and message_is(payload, "请输入用户名")
    return ok, describe(status, payload)


def test_reg_003():
    client = opener()
    status, payload = call(client, "POST", "/api/register", {"username": "abcde", "password": "Pass1234"})
    login_status, login_payload = call(
        opener(), "POST", "/api/login", {"username": "abcde", "password": "Pass1234"}
    )
    rejected = status != 201 and "用户名长度不足" in payload.get("message", "")
    cannot_login = login_status == 401 and message_is(login_payload, "用户名或密码错误")
    actual = f"注册：{describe(status, payload)}。登录：{describe(login_status, login_payload)}"
    return rejected and cannot_login, actual


def test_reg_004():
    status, payload = call(opener(), "POST", "/api/register", {"username": "apireg", "password": "Pass1234"})
    ok = status == 201 and message_is(payload, "注册成功")
    return ok, describe(status, payload)


def test_reg_005():
    status, payload = call(opener(), "POST", "/api/register", {"username": "apireg", "password": "Pass1234"})
    ok = status == 409 and message_is(payload, "用户名已存在")
    return ok, describe(status, payload)


def test_reg_006():
    status, payload = call(
        opener(), "POST", "/api/register", {"username": " apireg ", "password": "Pass1234"}
    )
    ok = status == 409 and message_is(payload, "用户名已存在")
    return ok, describe(status, payload)


def test_reg_007():
    status, payload = call(opener(), "POST", "/api/register", {"username": "newuser", "password": ""})
    ok = status == 400 and message_is(payload, "请输入密码")
    return ok, describe(status, payload)


def test_reg_008():
    created, created_body = call(
        opener(), "POST", "/api/register", {"username": "spaces", "password": " Pass1 "}
    )
    matched, matched_body = call(
        opener(), "POST", "/api/login", {"username": "spaces", "password": " Pass1 "}
    )
    trimmed, trimmed_body = call(
        opener(), "POST", "/api/login", {"username": "spaces", "password": "Pass1"}
    )
    ok = (
        created == 201
        and matched == 200
        and matched_body.get("username") == "spaces"
        and trimmed == 401
        and message_is(trimmed_body, "用户名或密码错误")
    )
    actual = (
        f"注册：{describe(created, created_body)}。"
        f"原样密码登录：{describe(matched, matched_body)}。"
        f"去掉空格后登录：{describe(trimmed, trimmed_body)}"
    )
    return ok, actual


def test_login_001():
    client = opener()
    status, payload = call(client, "POST", "/api/login", {"username": "", "password": "Pass1234"})
    ok = status == 400 and message_is(payload, "请输入用户名") and no_session(client)
    return ok, describe(status, payload)


def test_login_002():
    client = opener()
    status, payload = call(client, "POST", "/api/login", {"username": "   ", "password": "Pass1234"})
    ok = status == 400 and message_is(payload, "请输入用户名") and no_session(client)
    return ok, describe(status, payload)


def test_login_003():
    client = opener()
    status, payload = call(client, "POST", "/api/login", {"username": "apireg", "password": ""})
    ok = status == 400 and message_is(payload, "请输入密码") and no_session(client)
    return ok, describe(status, payload)


def test_login_004():
    client = opener()
    status, payload = call(client, "POST", "/api/login", {"username": "apireg", "password": "Pass1234"})
    me_status, me_payload = call(client, "GET", "/api/me")
    ok = status == 200 and payload.get("username") == "apireg" and me_status == 200 and me_payload.get("username") == "apireg"
    return ok, f"登录：{describe(status, payload)}。查询登录状态：{describe(me_status, me_payload)}"


def test_login_005():
    status, payload = call(opener(), "POST", "/api/login", {"username": " apireg ", "password": "Pass1234"})
    ok = status == 200 and payload.get("username") == "apireg"
    return ok, describe(status, payload)


def test_login_006():
    status, payload = call(opener(), "POST", "/api/login", {"username": "nouser", "password": "Pass1234"})
    ok = status == 401 and message_is(payload, "用户名或密码错误")
    return ok, describe(status, payload)


def test_login_007():
    missing, missing_body = call(opener(), "POST", "/api/login", {"username": "nouser", "password": "Pass1234"})
    status, payload = call(opener(), "POST", "/api/login", {"username": "apireg", "password": "Wrong999"})
    ok = (
        status == 401
        and message_is(payload, "用户名或密码错误")
        and payload.get("message") == missing_body.get("message")
    )
    return ok, f"{describe(status, payload)}。用户名不存在时为：{describe(missing, missing_body)}"


def test_session_001():
    client = opener()
    call(client, "POST", "/api/login", {"username": "apireg", "password": "Pass1234"})
    first_status, first = call(client, "GET", "/api/me")
    second_status, second = call(client, "GET", "/api/me")
    ok = (
        first_status == 200
        and second_status == 200
        and first.get("ok") is True
        and second.get("ok") is True
        and first.get("username") == "apireg"
        and second.get("username") == "apireg"
        and first.get("loggedInAt")
        and second.get("loggedInAt")
    )
    return ok, f"第一次：{describe(first_status, first)}。第二次：{describe(second_status, second)}"


def test_session_002():
    status, payload = call(opener(), "GET", "/api/me")
    ok = status == 401 and message_is(payload, "未登录")
    return ok, describe(status, payload)


def test_session_003():
    client = opener()
    call(client, "POST", "/api/login", {"username": "apireg", "password": "Pass1234"})
    status, payload = call(client, "POST", "/api/logout")
    me_status, me_payload = call(client, "GET", "/api/me")
    ok = message_is(payload, "已退出") and me_status == 401 and message_is(me_payload, "未登录")
    return ok, f"退出：{describe(status, payload)}。再次查询：{describe(me_status, me_payload)}"


def app_pids():
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -and $_.CommandLine -match 'app\\.py' } | "
        "ForEach-Object { \"$($_.ProcessId) $($_.ParentProcessId)\" }"
    )
    output = subprocess.check_output(["powershell", "-NoProfile", "-Command", command], text=True)
    processes = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            processes[int(parts[0])] = int(parts[1])
    return processes


def restart_server():
    processes = app_pids()
    roots = [pid for pid, parent in processes.items() if parent not in processes]
    for pid in roots:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True)
    deadline = time.time() + 15
    while time.time() < deadline:
        if not app_pids():
            break
        time.sleep(0.3)
    flags = 0x00000008 | 0x00000200
    subprocess.Popen(
        [str(PYTHON), "app.py"],
        cwd=BACKEND,
        creationflags=flags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            status, payload = call(opener(), "GET", "/api/health")
            if status == 200 and payload.get("ok") is True:
                return True, "账号服务已重启，健康检查通过"
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.4)
    return False, "重启后健康检查未通过"


def test_nf_002():
    restarted, note = restart_server()
    if not restarted:
        return False, note
    status, payload = call(opener(), "POST", "/api/login", {"username": "apireg", "password": "Pass1234"})
    ok = status == 200 and payload.get("username") == "apireg"
    return ok, f"{note}。登录：{describe(status, payload)}"


CASES = [
    ("TC-API-REG-001", test_reg_001),
    ("TC-API-REG-002", test_reg_002),
    ("TC-API-REG-003", test_reg_003),
    ("TC-API-REG-004", test_reg_004),
    ("TC-API-REG-005", test_reg_005),
    ("TC-API-REG-006", test_reg_006),
    ("TC-API-REG-007", test_reg_007),
    ("TC-API-REG-008", test_reg_008),
    ("TC-API-LOGIN-001", test_login_001),
    ("TC-API-LOGIN-002", test_login_002),
    ("TC-API-LOGIN-003", test_login_003),
    ("TC-API-LOGIN-004", test_login_004),
    ("TC-API-LOGIN-005", test_login_005),
    ("TC-API-LOGIN-006", test_login_006),
    ("TC-API-LOGIN-007", test_login_007),
    ("TC-API-SESSION-001", test_session_001),
    ("TC-API-SESSION-002", test_session_002),
    ("TC-API-SESSION-003", test_session_003),
    ("TC-API-NF-002", test_nf_002),
]


def main():
    clean_fixtures()
    for case_id, func in CASES:
        ok, actual = func()
        print(f"{'PASS' if ok else 'FAIL'} {case_id} {actual}")


if __name__ == "__main__":
    main()
