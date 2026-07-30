import asyncio
import csv
import os
from datetime import datetime
import zoneinfo # To fix the timestamp issue
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
# Add your local timezone here (e.g., "America/Los_Angeles", "Europe/London", etc.)
LOCAL_TZ = zoneinfo.ZoneInfo("America/Los_Angeles")

REGIONS = [
    {"url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Dynamis", "folder": "scraped_data"},
    {"url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Light", "folder": "scraped_data_eu"},
    {"url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Elemental", "folder": "scraped_data_jp"},
    {"url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Materia", "folder": "scraped_data_oc"}
]
TOTAL_PLAYERS = 300 

def clean_text(text: str) -> str:
    """Your original cleaning logic."""
    return " ".join(text.split())

async def scrape():
    async with async_playwright() as p:
        # Launch Firefox headless (Your original setup)
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )

        # Loop through each region
        for region in REGIONS:
            url = region["url"]
            folder = region["folder"]
            
            print(f"🚀 Scraping: {url}")
            os.makedirs(folder, exist_ok=True)

            page = await context.new_page()
            await page.goto(url)
            await page.wait_for_timeout(2000)

            # --- YOUR ORIGINAL LOGIC STARTS HERE ---
            
            # Handle cookie prompt
            try:
                accept_btn = page.locator("button:has-text('Accept')")
                if await accept_btn.count() > 0:
                    await accept_btn.click()
                    await page.wait_for_timeout(500)
            except:
                pass

            # Wait for the table container
            try:
                await page.wait_for_selector(".cc-ranking__table", timeout=45000)
                await page.evaluate("window.scrollBy(0, 100);")
                await page.wait_for_function("""
                () => document.querySelectorAll('.cc-ranking__table > div').length > 0
                """, timeout=45000)
            except:
                print(f"⚠️ Table not found for {folder}. Skipping.")
                await page.close()
                continue

            # Incremental scrolling (Your original loop)
            scroll_attempt = 0
            while scroll_attempt < 50:
                await page.evaluate("window.scrollBy(0, 800);")
                await page.wait_for_timeout(700)

                try:
                    show_more = page.locator("button:has-text('Show More')")
                    if await show_more.count() > 0:
                        await show_more.click()
                        await page.wait_for_timeout(500)
                except:
                    pass

                curr_rows = await page.locator(".cc-ranking__table > div").count()
                if curr_rows >= TOTAL_PLAYERS:
                    break
                scroll_attempt += 1

            # Scrape all rows (Your original data extraction)
            rows = await page.locator(".cc-ranking__table > div").all()
            data = []

            for row in rows:
                try:
                    rank = clean_text(await row.locator(".order").inner_text())
                    full_name = clean_text(await row.locator(".name").inner_text())

                    # Split Name / World
                    parts = full_name.split()
                    if len(parts) >= 2:
                        name = " ".join(parts[:2])
                        world = " ".join(parts[2:])
                    else:
                        name = full_name
                        world = ""

                    # Credits & Gained
                    points_text = clean_text(await row.locator(".points").inner_text())
                    points_parts = points_text.split()
                    credits = points_parts[0] if len(points_parts) > 0 else ""
                    credits_gained = points_parts[1].replace("+", "") if len(points_parts) > 1 else "0"

                    # Victories & Gained
                    wins_text = clean_text(await row.locator(".wins").inner_text())
                    wins_parts = wins_text.split()
                    victories = wins_parts[0] if len(wins_parts) > 0 else ""
                    victories_gained = wins_parts[1].replace("+", "") if len(wins_parts) > 1 else "0"

                    data.append({
                        "Rank": rank,
                        "Name": name,
                        "World": world,
                        "Credits": credits,
                        "Victories": victories,
                        "Credits Gained": credits_gained,
                        "Victories Gained": victories_gained
                    })
                except:
                    continue

            # Save CSV with Local Timezone
            date_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
            filename = os.path.join(folder, f"rankings_{date_str}.csv")

            if data:
                with open(filename, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                print(f"✅ Saved {len(data)} players to {filename}")

            await page.close() # Close page before next region

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
