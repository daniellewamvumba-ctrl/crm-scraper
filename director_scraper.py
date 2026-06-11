import csv
import asyncio
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def extract_emails_from_text(text):
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(pattern, text)))

async def deep_scan_website(context, url):
    try:
        new_page = await context.new_page()
        await new_page.goto(url, wait_until="commit", timeout=12000)
        page_text = await new_page.locator("body").inner_text()
        emails = await extract_emails_from_text(page_text)
        await new_page.close()
        return ", ".join(emails) if emails else "N/A"
    except Exception:
        return "N/A"

async def scrape_directory():
    stealth_engine = Stealth()
    async with async_playwright() as p:
        # Launch browser (headless must be False so you can type)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        await stealth_engine.apply_stealth_async(context)
        page = await context.new_page()

        # Step 1: Just land on the homepage
        print("Opening YellowPages browser window...")
        await page.goto("https://yellowpages.com", wait_until="commit")

        # Step 2: Pause script and pass control to your hands
        print("\n" + "="*60)
        print("ACTION REQUIRED:")
        print("1. Click inside the browser window.")
        print("2. Type your business keyword and location manually.")
        print("3. Click the Search button to reveal the listings grid.")
        print("4. ONCE YOU SEE THE RESULTS, click back inside this terminal.")
        print("5. Press the [ENTER] key here to launch the automated extractor.")
        print("="*60 + "\n")
        
        # This python input statement cleanly halts the async engine execution
        input("Press [ENTER] here after the search results load on your screen...")

        raw_leads = []
        page_num = 1
        max_pages = 2  # Adjust if you want to paginate through more pages manually

        while page_num <= max_pages:
            print(f"\n--- Scraping Layout Grid: Page {page_num} ---")
            
            # Smooth scroll down to wake up lazy elements
            for _ in range(3):
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(1)

            # Targets the actual listing card container layouts on the screen
            business_cards = page.locator("div.result, div[id^='lid-'], .info")
            count = await business_cards.count()
            print(f"Detected {count} business items on this view.")

            for i in range(count):
                try:
                    card = business_cards.nth(i)
                    
                    name_el = card.locator("a.business-name").first
                    name = await name_el.inner_text() if await name_el.count() > 0 else f"Company {i}"

                    phone_el = card.locator("div.phones, .phone").first
                    phone = await phone_el.inner_text() if await phone_el.count() > 0 else "N/A"
                    
                    website_el = card.locator("a.track-visit-website").first
                    website_url = await website_el.get_attribute("href") if await website_el.count() > 0 else None
                    
                    email = "N/A"
                    if website_url and "yellowpages.com" not in website_url:
                        print(f"Scanning web link: {website_url}")
                        email = await deep_scan_website(context, website_url)

                    raw_leads.append({
                        "Company Name": name.strip(),
                        "Phone": phone.strip(),
                        "Website": website_url if website_url else "N/A",
                        "Raw Email": email
                    })
                    print(f"[{len(raw_leads)}] Extracted: {name.strip()}")
                except Exception as e:
                    print(f"Skipping index card entry {i}: {e}")

            # Pagination automation check step
            next_button = page.locator("a.next, [class*='next']").first
            if await next_button.count() > 0 and page_num < max_pages:
                print("Advancing to next search results layout layout page...")
                await next_button.click()
                await page.wait_for_load_state("networkidle")
                page_num += 1
            else:
                print("Extraction phase finished.")
                break

        # Save the dataset securely
        if raw_leads:
            headers = ["Company Name", "Phone", "Website", "Raw Email"]
            with open("raw_leads.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(raw_leads)
            print(f"\nSuccess! Total of {len(raw_leads)} entries written to 'raw_leads.csv'")
        else:
            print("\nError: The script failed to find listing cards on your current page layout view.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_directory())


