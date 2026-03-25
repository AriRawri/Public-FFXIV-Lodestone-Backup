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
    return " ".join(text.split()) if text else ""

async def scrape_region(browser_context, region_info):
    name = region_info["name"]
    url = region_info["url"]
    folder = region_info["folder"]
    
    print(f"🌐 Processing {name.upper()}...")
    os.makedirs(folder, exist_ok=True)

    page = await browser_context.new_page()
    
    try:
        # Increase timeout for slow GitHub runners
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000) 

        # 1. Handle Cookies
        try:
            accept_btn = page.locator("button:has-text('Accept')")
            if await accept_btn.count() > 0:
                await accept_btn.click()
        except:
            pass

        # 2. Wait for Table
        await page.wait_for_selector(".cc-ranking__table", timeout=30000)
        
        # 3. Aggressive Scrolling
        for i in range(40):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(800)
            
            # Click "Show More" if it appears
            show_more = page.get_by_role("button", name="Show More")
            if await show_more.is_visible():
                await show_more.click()
            
            count = await page.locator(".cc-ranking__table > div").count()
            if count >= TOTAL_PLAYERS:
                print(f"✅ Found {count} rows for {name}")
                break

        # 4. Data Extraction
        rows = await page.locator(".cc-ranking__table > div").all()
        data = []
        
        for row in rows:
            try:
                # Scrape fields using more specific locators
                rank = await row.locator(".order").inner_text()
                full_name = await row.locator(".name").inner_text()
                points = await row.locator(".points").inner_text()
                wins = await row.locator(".wins").inner_text()

                p_parts = clean_text(points).split()
                w_parts = clean_text(wins).split()

                data.append({
                    "Rank": clean_text(rank),
                    "Name": clean_text(full_name),
                    "Credits": p_parts[0] if p_parts else "0",
                    "Victories": w_parts[0] if w_parts else "0",
                    "Credits Gained": p_parts[1].replace("+", "") if len(p_parts) > 1 else "0",
                    "Victories Gained": w_parts[1].replace("+", "") if len(w_parts) > 1 else "0"
                })
            except Exception as e:
                continue

        # 5. Save Results
        if data:
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = os.path.join(folder, f"rankings_{name}_{date_str}.csv")
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            print(f"💾 File created: {filename}")
        else:
            print(f"❌ No data extracted for {name}")

    except Exception as e:
        print(f"🛑 Error scraping {name}: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        # Higher quality User Agent to avoid bot detection
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        for region in REGIONS:
            await scrape_region(context, region)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
