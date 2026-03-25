import asyncio
import csv
import os
from datetime import datetime
from playwright.async_api import async_playwright

# Configuration for all regions
REGIONS = [
    {"name": "na", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Dynamis", "folder": "scraped_data"},
    {"name": "eu", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Light", "folder": "scraped_data_eu"},
    {"name": "jp", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Elemental", "folder": "scraped_data_jp"},
    {"name": "oc", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Materia"}
]

TOTAL_PLAYERS = 300 

def clean_text(text: str) -> str:
    return " ".join(text.split())

async def scrape_region(browser_context, region_info):
    url = region_info["url"]
    folder = region_info.get("folder", f"scraped_data_{region_info['name']}")
    
    print(f"🌐 Starting scrape for region: {region_info['name'].upper()}")
    os.makedirs(folder, exist_ok=True)

    page = await browser_context.new_page()
    await page.goto(url)
    await page.wait_for_timeout(2000)

    # Handle cookie prompt
    try:
        accept_btn = page.locator("button:has-text('Accept')")
        if await accept_btn.count() > 0:
            await accept_btn.click()
            await page.wait_for_timeout(500)
    except:
        pass

    # Table detection and scrolling
    try:
        await page.wait_for_selector(".cc-ranking__table", timeout=45000)
        await page.evaluate("window.scrollBy(0, 100);")
    except:
        print(f"⚠️ Table not found for {region_info['name']}. Skipping.")
        await page.close()
        return

    curr_rows = 0
    for _ in range(50):
        await page.evaluate("window.scrollBy(0, 800);")
        await page.wait_for_timeout(700)
        
        try:
            show_more = page.locator("button:has-text('Show More')")
            if await show_more.count() > 0:
                await show_more.click()
        except:
            pass

        curr_rows = await page.locator(".cc-ranking__table > div").count()
        if curr_rows >= TOTAL_PLAYERS:
            break

    # Scrape data
    rows = await page.locator(".cc-ranking__table > div").all()
    data = []
    for row in rows:
        try:
            rank = clean_text(await row.locator(".order").inner_text())
            full_name = clean_text(await row.locator(".name").inner_text())
            parts = full_name.split()
            name = " ".join(parts[:2]) if len(parts) >= 2 else full_name
            world = " ".join(parts[2:]) if len(parts) >= 2 else ""

            points_text = clean_text(await row.locator(".points").inner_text()).split()
            wins_text = clean_text(await row.locator(".wins").inner_text()).split()

            data.append({
                "Rank": rank,
                "Name": name,
                "World": world,
                "Credits": points_text[0] if points_text else "",
                "Victories": wins_text[0] if wins_text else "",
                "Credits Gained": points_text[1].replace("+", "") if len(points_text) > 1 else "0",
                "Victories Gained": wins_text[1].replace("+", "") if len(wins_text) > 1 else "0"
            })
        except:
            continue

    # Save CSV
    if data:
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(folder, f"crystalline_conflict_{region_info['name']}_{date_str}.csv")
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print(f"✅ Saved {len(data)} players to {filename}")
    
    await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/114.0",
            viewport={"width": 1280, "height": 800},
        )
        
        for region in REGIONS:
            await scrape_region(context, region)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
