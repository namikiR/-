# monitor.py
import os, json, sys, time
from pathlib import Path
from urllib import request
from playwright.sync_api import sync_playwright

URL = "https://app.spirinc.com/t/fANh0B70nMYWrpDAoiR4v/as/Mx59HIi4Tr1ZF97UGEDVC/confirm-guest"
STATE = Path("state.json")

# ▼ここを実ページのDOMに合わせて調整（例：data属性やテキスト一致など）
AVAILABLE_SELECTOR = "[data-test='slot'][data-status='available'], .slot.available, text=空き"

def notify_line(msg: str):
    token = os.getenv("LINE_TOKEN")
    if not token:
        return
    data = request.urlopen(
        request.Request(
            "https://notify-api.line.me/api/notify",
            data=f"message={msg}".encode(),
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
    ).read()

def notify_slack(msg: str):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return
    body = json.dumps({"text": msg}).encode()
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"})
    request.urlopen(req).read()

def load_prev():
    if STATE.exists():
        return json.loads(STATE.read_text()).get("count", 0)
    return 0

def save_now(count: int):
    STATE.write_text(json.dumps({"count": count}))

def main():
    prev = load_prev()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()

        # Cookie注入（ログインが必要な場合）
        cname = os.getenv("SPIR_COOKIE_NAME")
        cval = os.getenv("SPIR_COOKIE_VALUE")
        cdomain = os.getenv("SPIR_COOKIE_DOMAIN")
        if cname and cval and cdomain:
            context.add_cookies([{
                "name": cname, "value": cval,
                "domain": cdomain, "path": "/",
                "httpOnly": True, "secure": True
            }])

        page = context.new_page()
        page.goto(URL, wait_until="networkidle")

        # 充分に描画されるまで少し待機（動的サイト対策）
        time.sleep(2)

        # 空き枠カウント
        available = page.locator(AVAILABLE_SELECTOR)
        count = available.count()

        # 差分通知
        if count > prev:
            msg = f"Spirincの空き枠が増えました：{prev} → {count}（{URL}）"
            notify_line(msg)
            notify_slack(msg)

        save_now(count)
        browser.close()

if __name__ == "__main__":
    main()
