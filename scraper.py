import asyncio
import csv
import os
from datetime import datetime
from playwright.async_api import async_playwright

# Region Configuration
REGIONS = [
    {"name": "na", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Dynamis", "folder": "scraped_data"},
    {"name": "eu", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Light", "folder": "scraped_data_eu"},
    {"name": "jp", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Elemental", "folder": "scraped_data_jp"},
    {"name": "oc", "url": "https://na.finalfantasyxiv.com/lodestone/ranking/crystallineconflict/?dcgroup=Materia", "folder": "scraped_data_oc"}
]

TOTAL_PLAYERS = 300 

def clean_text(text: str) -> str:
    return " ".join(text.split()) if text else ""

async def scrape():
    async with async_playwright() as p:
        # Using Firefox as per your original script
        browser = await p.firefox.launch(headless=True)
        
        # New context for each run to keep it clean
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        for region in REGIONS:
            print(f"🌐 Scraping Region: {region['name'].upper()}")
            os.makedirs(region['folder'], exist_ok=True)
            
            page = await context.new_page()
            try:
                await page.goto(region['url'], wait_until="load", timeout=60000)
                await page.wait_for_timeout(2000)

                # Cookie Consent
                try:
                    btn = page.locator("button:has-text('Accept')")
                    if await btn.count() > 0:
                        await btn.click()
                except:
                    pass

                # Wait for table
                await page.wait_for_selector(".cc-ranking__table", timeout=30000)

                # Scrolling (Matches your original working logic)
                for _ in range(40):
                    await page.evaluate("window.scrollBy(0, 1000);")
                    await page.wait_for_timeout(700)
                    
                    try:
                        show_more = page.locator("button:has-text('Show More')")
                        if await show_more.count() > 0:
                            await show_more.click()
                    except:
                        pass

                    count = await page.locator(".cc-ranking__table > div").count()
                    if count >= TOTAL_PLAYERS:
                        break

                # Extraction
                rows = await page.locator(".cc-ranking__table > div").all()
                data = []
                for row in rows:
                    try:
                        rank = await row.locator(".order").inner_text()
                        full_name = await row.locator(".name").inner_text()
                        points = await row.locator(".points").inner_text()
                        wins = await row.locator(".wins").inner_text()

                        # Split name and world
                        parts = full_name.split()
                        name = " ".join(parts[:2]) if len(parts) >= 2 else full_name
                        world = " ".join(parts[2:]) if len(parts) >= 2 else ""

                        data.append({
                            "Rank": clean_text(rank),
                            "Name": clean_text(name),
                            "World": clean_text(world),
                            "Credits": clean_text(points).split()[0] if points else "0",
                            "Victories": clean_text(wins).split()[0] if wins else "0"
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
                    print(f"✅ Created {filename} with {len(data)} rows.")
                else:
                    print(f"❌ No data found for {region['name']}")

            except Exception as e:
                print(f"⚠️ Error in {region['name']}: {e}")
            finally:
                await page.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
