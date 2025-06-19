import sys
import asyncio
from playwright.async_api import async_playwright
import os

# Accept URL and doc_id as arguments
if len(sys.argv) > 2:
    URL = sys.argv[1]
    doc_id = sys.argv[2]

# Folder to save outputs
os.makedirs("output", exist_ok=True)

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL)
        
        # Take screenshot
        await page.screenshot(path=f"output/{doc_id}_screenshot.png", full_page=True)
        print(f"Screenshot saved as output/{doc_id}_screenshot.png ✅")

        # Extract text content
        content = await page.locator('#mw-content-text').inner_text()
        with open(f"output/{doc_id}.txt", "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Content saved as output/{doc_id}.txt ✅")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
