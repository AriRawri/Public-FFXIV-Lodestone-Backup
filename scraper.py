import asyncio
import csv
import os
from datetime import datetime
from playwright.async_api import async_playwright

URL = "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Dynamis"
DATA_FOLDER = "scraped_data"
TOTAL_PLAYERS = 300  # stop scrolling once we reach this number

def clean_text(text: str) -> str:
    """Remove newlines and extra spaces to make CSV safe."""
    return " ".join(text.split())

async def scrape():
    os.makedirs(DATA_FOLDER, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context()

        # Start tracing
        await context.tracing.start(
            screenshots=True,
            snapshots=True,
            sources=True
        )

        page = await context.new_page()
        await page.goto(URL)

        # Handle cookie prompt
        try:
            accept_btn = page.locator("button:has-text('Accept')")
            if await accept_btn.count() > 0:
                await accept_btn.click()
                print("🍪 Cookie consent accepted")
                await page.wait_for_timeout(500)
        except:
            print("🍪 No cookie prompt detected")

        # Wait for table (retry once if needed)
        try:
            await page.wait_for_selector(".cc-ranking__table", timeout=15000)
        except:
            print("⚠️ Table not found, retrying once...")
            await page.reload()
            try:
                await page.wait_for_selector(".cc-ranking__table", timeout=15000)
            except:
                print("❌ Table not found after reload. Exiting.")
                await context.tracing.stop(path="trace.zip")
                await browser.close()
                return

        # Incremental scrolling until 300 rows
        scroll_increment = 800
        max_scroll_attempts = 50
        scroll_attempt = 0
        curr_rows = 0

        while scroll_attempt < max_scroll_attempts:
            await page.evaluate(f"window.scrollBy(0, {scroll_increment});")
            await page.wait_for_timeout(700)

            # Optional: Show More button
            try:
                show_more = page.locator("button:has-text('Show More')")
                if await show_more.count() > 0:
                    await show_more.click()
                    await page.wait_for_timeout(500)
            except:
                pass

            curr_rows = await page.locator(".cc-ranking__table > div").count()
            print(f"Scrolling... rows detected: {curr_rows}")

            if curr_rows >= TOTAL_PLAYERS:
                print("✅ All 300 players detected")
                await page.wait_for_timeout(1500)
                break

            scroll_attempt += 1

        # Scrape all rows
        rows = await page.locator(".cc-ranking__table > div").all()
        data = []

        for row in rows:
            try:
                rank = clean_text(await row.locator(".order").inner_text())

                # Name + World combined
                full_name = clean_text(await row.locator(".name").inner_text())

                # Split into Name (first two words) and World (rest)
                parts = full_name.split()
                if len(parts) >= 2:
                    name = " ".join(parts[:2])
                    world = " ".join(parts[2:])
                else:
                    name = full_name
                    world = ""

                # Credits
                points_text = clean_text(await row.locator(".points").inner_text())
                parts = points_text.split()
                credits = parts[0] if len(parts) > 0 else ""
                credits_gained = parts[1] if len(parts) > 1 else ""

                # Victories
                wins_text = clean_text(await row.locator(".wins").inner_text())
                parts = wins_text.split()
                victories = parts[0] if len(parts) > 0 else ""
                victories_gained = parts[1] if len(parts) > 1 else ""

                # Remove + symbol if present
                credits_gained = credits_gained.replace("+", "")
                victories_gained = victories_gained.replace("+", "")

                data.append({
                    "Rank": rank,
                    "Name": name,
                    "World": world,
                    "Credits": credits,
                    "Victories": victories,
                    "Credits Gained": credits_gained,
                    "Victories Gained": victories_gained
                })

            except Exception as e:
                print(f"⚠️ Skipping a row due to error: {e}")
                continue

        # Save CSV
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(DATA_FOLDER, f"crystalline_conflict_rankings_{date_str}.csv")

        if data:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            print(f"✅ Scraped {len(data)} players. Saved to {filename}")
        else:
            print("⚠️ No data found. CSV not created.")

        # Save trace
        await context.tracing.stop(path="trace.zip")
        await browser.close()

asyncio.run(scrape())

