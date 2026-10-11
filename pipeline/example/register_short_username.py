# 示例：打开注册页，用不足 6 位的用户名提交，把页面实际结果打到标准输出。
# 退出码 0 表示出现预期文案「用户名长度不足」，退出码 1 表示没有出现。
#
# 运行前先启动前端 http://localhost:5173 和账号服务 http://localhost:5000。
# 安装：
#   pip install playwright
#   python -m playwright install chromium
# 运行（仓库根目录）：
#   python pipeline/example/register_short_username.py

import sys

from playwright.sync_api import sync_playwright

WEB = "http://localhost:5173/register"
EXPECTED = "用户名长度不足"
SCREENSHOT = "pipeline/example/last-result.png"


def main() -> int:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(WEB, wait_until="networkidle", timeout=15000)
            page.get_by_label("用户名").fill("abc")
            page.get_by_label("密码").fill("Pass1234")
            page.get_by_label("确认密码").fill("Pass1234")
            page.get_by_role("button", name="注册").click()
            page.wait_for_timeout(1000)
            body = page.locator("body").inner_text()
            passed = EXPECTED in body
            actual = EXPECTED if passed else body.replace("\n", " ")[:200]
            url = page.url
        except Exception as error:
            passed = False
            actual = f"未能完成操作：{error}"
            url = ""
        finally:
            page.screenshot(path=SCREENSHOT, full_page=True)
            browser.close()

    print("【执行结果】")
    print("用例：TC-UI-REG-002")
    print("结果：通过" if passed else "结果：失败")
    print(f"预期：{EXPECTED}")
    print(f"实际：{actual}")
    print(f"地址：{url}")
    print(f"截图：{SCREENSHOT}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
