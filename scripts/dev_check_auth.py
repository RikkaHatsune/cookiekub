"""Проверка KubanoID, кабинета, поддержки и 403 через Edge."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"


def main() -> int:
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda msg: errors.append(f"console {msg.type}: {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

        # 1. Гость на админке → 403 с формой входа
        page.goto(BASE + "/admin.html", wait_until="networkidle")
        page.wait_for_url("**/403.html?reason=auth&next=admin.html", timeout=10000)
        print("403 title:", page.locator("h1").inner_text())
        page.screenshot(path=str(OUT / "dev-403-guest.png"), full_page=True)

        # 2. Вход обычным пользователем
        page.goto(BASE + "/login.html", wait_until="networkidle")
        page.screenshot(path=str(OUT / "dev-login.png"), full_page=True)
        page.fill("#login-email", "user@cookiekub.ru")
        page.fill("#login-password", "User123!")
        page.click("#login-submit")
        page.wait_for_url("**/account.html", timeout=10000)
        page.wait_for_timeout(500)
        print("account heading:", page.locator("h1").first.inner_text())
        page.screenshot(path=str(OUT / "dev-account.png"), full_page=True)

        # 3. Пользователь на админке → 403 с note
        page.goto(BASE + "/admin.html", wait_until="networkidle")
        page.wait_for_url("**/403.html?reason=admin&next=admin.html", timeout=10000)
        page.wait_for_timeout(400)
        print("403 user note:", page.locator("#forbidden-user-note").inner_text() if page.locator("#forbidden-user-note").count() else "нет")
        page.screenshot(path=str(OUT / "dev-403-user.png"), full_page=True)

        # 4. Выход через 403
        page.click("#forbidden-logout")
        page.wait_for_timeout(600)
        print("after logout url:", page.url)

        # 5. Регистрация нового KubanoID
        email = f"e2e-{int(time.time())}@example.com"
        page.goto(BASE + "/register.html", wait_until="networkidle")
        page.screenshot(path=str(OUT / "dev-register.png"), full_page=True)
        page.fill("#register-name", "Тестовый Пекарь")
        page.fill("#register-email", email)
        page.fill("#register-password", "Cookies123!")
        page.check("#register-consent")
        page.click("#register-submit")
        page.wait_for_url("**/account.html", timeout=10000)
        page.wait_for_timeout(500)
        print("registered:", email)
        page.screenshot(path=str(OUT / "dev-account-new.png"), full_page=True)

        # 6. Поддержка: тикет от авторизованного
        page.goto(BASE + "/support.html", wait_until="networkidle")
        page.wait_for_timeout(800)
        page.on("response", lambda r: print("TICKET RESP", r.status, r.text()[:200]) if "/api/tickets" in r.url else None)
        print("support hidden field:", page.locator("#support-email-field").get_attribute("hidden"))
        print("support email required:", page.locator("#support-email").get_attribute("required"))
        page.fill("#support-subject", "Тестовое обращение из e2e")
        page.fill("#support-message", "Проверяем форму поддержки и имитацию письма.")
        page.select_option("#support-category", "bug")
        page.click("#support-submit")
        page.wait_for_timeout(3000)
        print("support error:", page.locator("#support-error").inner_text())
        print("support success hidden:", page.locator("#support-success").get_attribute("hidden"))
        page.screenshot(path=str(OUT / "dev-support.png"), full_page=True)

        browser.close()

    if errors:
        print("ERRORS:")
        for error in errors:
            print(" ", error)
        return 1
    print("AUTH OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
