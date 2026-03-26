import asyncio
import csv
import os
from datetime import datetime
from playwright.async_api import async_playwright

# Configuration
REGIONS = [
    {"name": "na", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Dynamis", "folder": "scraped_data"},
    {"name": "eu", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Light", "folder": "scraped_data_eu"},
    {"name": "jp", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Elemental", "folder": "scraped_data_jp"},
    {"name": "oc", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Materia", "folder": "scraped_data_oc"}
]

TOTAL_PLAYERS = 300 

def clean_text(text: str) -> str:
    return " ".join(text.split())

async def scrape():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )

        for region in REGIONS:
            print(f"🔎 Starting {region['name'].upper()}...")
            os.makedirs(region['folder'], exist_ok=True)
            
            page = await context.new_page()
            await page.goto(region['url'])
            await page.wait_for_timeout(3000)

            # Cookie Acceptance
            try:
                accept_btn = page.locator("button:has-text('Accept')")
                if await accept_btn.count() > 0:
                    await accept_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass

            # Scrolling logic (Your original version)
            scroll_attempt = 0
            while scroll_attempt < 40:
                await page.evaluate("window.scrollBy(0, 1000);")
                await page.wait_for_timeout(800)
                
                # Try clicking Show More
                try:
                    show_more = page.locator("button:has-text('Show More')")
                    if await show_more.count() > 0:
                        await show_more.click()
                except:
                    pass

                curr_rows = await page.locator(".cc-ranking__table > div").count()
                if curr_rows >= TOTAL_PLAYERS:
                    break
                scroll_attempt += 1

            # Scrape rows
            rows = await page.locator(".cc-ranking__table > div").all()
            data = []
            for row in rows:
                try:
                    rank = clean_text(await row.locator(".order").inner_text())
                    full_name = clean_text(await row.locator(".name").inner_text())
                    
                    # Name/World Split
                    parts = full_name.split()
                    name = " ".join(parts[:2]) if len(parts) >= 2 else full_name
                    world = " ".join(parts[2:]) if len(parts) >= 2 else ""

                    points_text = clean_text(await row.locator(".points").inner_text()).split()
                    credits = points_text[0] if points_text else ""
                    
                    wins_text = clean_text(await row.locator(".wins").inner_text()).split()
                    victories = wins_text[0] if wins_text else ""

                    data.append({
                        "Rank": rank, "Name": name, "World": world,
                        "Credits": credits, "Victories": victories
                    })
                except:
                    continue

            # Save CSV
            if data:
                date_str = datetime.now().strftime("%Y-%m-%d")
                filename = os.path.join(region['folder'], f"rankings_{region['name']}_{date_str}.csv")
                with open(filename, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                print(f"✅ Saved {len(data)} rows to {filename}")
            else:
                print(f"⚠️ No data found for {region['name']}")
            
            await page.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
