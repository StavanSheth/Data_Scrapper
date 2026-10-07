"""Playwright-based deterministic Google Maps scraper."""

import asyncio
import re
from typing import AsyncGenerator, Optional, Callable, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from app.core.domain.models import RawGoogleRecord
from app.scraping.maps.parser import GoogleMapsParser
from app.config.settings import settings

class GoogleMapsScraper:
    def __init__(
        self,
        headless: bool = True,
        max_retries: int = 2,
        request_timeout: int = 30000,
    ):
        self.headless = headless
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.parser = GoogleMapsParser()

    async def scrape(
        self,
        city: str,
        category: str,
        limit: int,
        run_id: str,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> AsyncGenerator[RawGoogleRecord, None]:
        """
        Scrapes Google Maps for a given category and city up to limit.
        Yields RawGoogleRecord as each business is discovered.
        """
        query = f"{category} in {city}".strip()
        encoded_query = query.replace(" ", "+")
        search_url = f"https://www.google.com/maps/search/{encoded_query}"

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            context: BrowserContext = await browser.new_context(
                locale="en-US",
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            page: Page = await context.new_page()

            try:
                # 1. Navigate to Google Maps search
                await self._navigate_with_retry(page, search_url)

                # 2. Handle consent modal if present
                await self._handle_consent(page)

                # 3. Wait for search results container
                feed_found = await self._wait_for_feed(page)
                if not feed_found:
                    return

                # 4. Stream results
                seen_place_ids: set[str] = set()
                seen_urls: set[str] = set()
                count_yielded = 0
                scroll_attempts = 0
                max_scroll_attempts = max(10, (limit // 5) + 5)

                while count_yielded < limit and scroll_attempts < max_scroll_attempts:
                    if cancel_check and cancel_check():
                        break

                    # Collect all place links in feed
                    links = await page.query_selector_all('a[href*="/maps/place/"]')

                    for link in links:
                        if count_yielded >= limit:
                            break
                        if cancel_check and cancel_check():
                            break

                        try:
                            href = await link.get_attribute("href")
                            if not href or href in seen_urls:
                                continue
                            seen_urls.add(href)

                            aria_name = await link.get_attribute("aria-label")
                            place_id, lat, lon = self.parser.extract_place_id_and_coords(href)

                            if place_id and place_id in seen_place_ids:
                                continue
                            if place_id:
                                seen_place_ids.add(place_id)

                            # Parse text from card as baseline
                            card_parent = await link.evaluate_handle('el => el.closest("div[jsaction]")')
                            card_text = await card_parent.inner_text() if card_parent else ""
                            card_lines = [l.strip() for l in card_text.split("\n") if l.strip()]
                            card_info = self.parser.parse_card_lines(card_lines, default_category=category)

                            business_name = aria_name or card_info.get("name") or "Unknown"

                            # Click card to open detail view for full phone/address/website
                            phone = None
                            website = None
                            address = card_info.get("address")
                            rating = card_info.get("rating")
                            review_count = card_info.get("review_count")
                            opening_hours = card_info.get("opening_hours")

                            try:
                                await link.click(timeout=3000)
                                await page.wait_for_timeout(1000)

                                # Address button
                                addr_btn = await page.query_selector('button[data-item-id="address"]')
                                if addr_btn:
                                    raw_addr = await addr_btn.get_attribute("aria-label")
                                    address = self.parser.clean_text_field("address", raw_addr) or address

                                # Phone button
                                phone_btn = await page.query_selector('button[data-item-id*="phone"]')
                                if phone_btn:
                                    raw_phone = await phone_btn.get_attribute("aria-label")
                                    phone = self.parser.clean_text_field("phone", raw_phone)

                                # Website authority button
                                web_btn = await page.query_selector('a[data-item-id="authority"]')
                                if web_btn:
                                    website = await web_btn.get_attribute("href")

                                # Rating
                                if rating is None:
                                    rating_el = await page.query_selector('span[aria-label*="stars"], span[aria-label*="star"]')
                                    if rating_el:
                                        r_text = await rating_el.get_attribute("aria-label")
                                        r_match = re.search(r"(\d+\.\d+)", r_text or "")
                                        if r_match:
                                            rating = float(r_match.group(1))

                                # Review count
                                if review_count is None:
                                    rev_el = await page.query_selector('button[aria-label*="reviews"]')
                                    if rev_el:
                                        rev_text = await rev_el.get_attribute("aria-label")
                                        rev_match = re.search(r"([\d,]+)\s+reviews", rev_text or "")
                                        if rev_match:
                                            review_count = int(rev_match.group(1).replace(",", ""))

                            except Exception:
                                # Non-fatal error while reading detail panel; card info is retained
                                pass

                            raw_record = RawGoogleRecord(
                                place_id=place_id,
                                name=business_name,
                                category=card_info.get("category") or category,
                                address=address,
                                phone=phone,
                                website=website,
                                rating=rating,
                                review_count=review_count,
                                opening_hours=opening_hours,
                                profile_url=href,
                                latitude=lat,
                                longitude=lon,
                                status="SUCCESS",
                                raw_payload={
                                    "city": city,
                                    "category": category,
                                    "card_lines": card_lines[:6],
                                },
                            )

                            count_yielded += 1
                            yield raw_record

                        except Exception:
                            # A single record extraction failure must not crash the run
                            continue

                    # Scroll feed to load more places
                    if count_yielded < limit:
                        scroll_attempts += 1
                        feed = await page.query_selector('div[role="feed"]')
                        if feed:
                            await page.evaluate('(el) => el.scrollTop = el.scrollHeight', feed)
                            await page.wait_for_timeout(2000)
                        else:
                            break

                        # Check if end of list reached
                        end_text = await page.query_selector('text="You\'ve reached the end of the list"')
                        if end_text:
                            break

            finally:
                await page.close()
                await context.close()
                await browser.close()

    async def _navigate_with_retry(self, page: Page, url: str) -> None:
        """Navigates to URL with retry for transient errors."""
        for attempt in range(self.max_retries + 1):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.request_timeout)
                await page.wait_for_timeout(2000)
                return
            except Exception as e:
                if attempt == self.max_retries:
                    raise e
                await asyncio.sleep(2)

    async def _handle_consent(self, page: Page) -> None:
        """Accepts Google cookies/consent popup if shown."""
        try:
            consent_btn = await page.wait_for_selector(
                'button[aria-label*="Accept all"], form[action*="consent"] button',
                timeout=3000,
            )
            if consent_btn:
                await consent_btn.click()
                await page.wait_for_timeout(1500)
        except Exception:
            pass

    async def _wait_for_feed(self, page: Page) -> bool:
        """Waits for the search feed or places to appear."""
        try:
            await page.wait_for_selector('div[role="feed"], a[href*="/maps/place/"]', timeout=15000)
            return True
        except Exception:
            return False
