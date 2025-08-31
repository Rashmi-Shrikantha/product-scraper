#!/usr/bin/env python3
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_FILE = "products.json"
STORAGE_FILE = "storage_state.json"
LOGIN_URL = "https://idenhq.com/login"          # update if different
APP_URL   = "https://idenhq.com/challenge"      # update if different

USERNAME = "your_username"   # <-- replace with your username
PASSWORD = "your_password"   # <-- replace with your password

def login_and_save(page):
    page.goto(LOGIN_URL)
    # fill credentials (update selectors if labels differ)
    page.fill('input[name="email"]', USERNAME)
    page.fill('input[name="password"]', PASSWORD)
    page.click('button:has-text("Sign in")')
    page.wait_for_load_state("networkidle")
    page.context.storage_state(path=STORAGE_FILE)

def scrape_cards(page):
    # keep scrolling until all products load
    prev_count, stable_rounds = 0, 0
    while stable_rounds < 3:   # stop when no new cards after 3 scrolls
        page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        time.sleep(1.5)
        count = page.locator("div:has-text('ID:')").count()
        if count == prev_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
        prev_count = count

    print(f"Total products loaded: {prev_count}")

    # extract product details
    cards = page.locator("div:has-text('ID:')")   # each product card
    results = []
    for i in range(cards.count()):
        card = cards.nth(i)
        text = card.inner_text().splitlines()
        product = {}
        for line in text:
            if ":" in line:
                key, val = line.split(":", 1)
                product[key.strip()] = val.strip()
            else:
                if "name" not in product:
                    product["name"] = line.strip()
        results.append(product)
    return results

def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        if Path(STORAGE_FILE).exists():
            context = browser.new_context(storage_state=STORAGE_FILE)
        else:
            context = browser.new_context()
        page = context.new_page()

        # check session
        try:
            page.goto(APP_URL, timeout=10000)
            page.wait_for_selector("text=Product Inventory", timeout=5000)
        except:
            login_and_save(page)
            page.goto(APP_URL)
            page.wait_for_selector("text=Product Inventory")

        # scrape
        data = scrape_cards(page)

        # save JSON
        Path(OUTPUT_FILE).write_text(json.dumps(data, indent=2))
        print(f"Saved {len(data)} products → {OUTPUT_FILE}")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
