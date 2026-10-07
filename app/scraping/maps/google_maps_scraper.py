"""Multi-strategy resilient Google Maps scraper using Playwright."""

import asyncio
import re
from typing import AsyncGenerator, Optional, Callable, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, ElementHandle
from app.core.domain.models import RawGoogleRecord
from app.scraping.maps.parser import GoogleMapsParser
from app.config.settings import settings

class GoogleMapsScraper:
    def __init__(
        self,
        headless: Optional[bool] = None,
        max_retries: Optional[int] = None,
        request_timeout: Optional[int] = None,
    ):
        self.headless = headless if headless is not None else settings.headless_browser
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self.request_timeout = request_timeout if request_timeout is not None else settings.browser_timeout_ms
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
        Scrapes Google Maps using multi-strategy fallback extraction.
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
                user_agent=settings.browser_user_agent,
            )
            page: Page = await context.new_page()

            try:
                # 1. Navigate with retry
                await self._navigate_with_retry(page, search_url)

                # 2. Dismiss cookie consent if shown
                await self._handle_consent(page)

                # 3. Wait for feed or place elements
                feed_found = await self._wait_for_feed(page)
                if not feed_found:
                    return

                seen_place_ids: set[str] = set()
                seen_urls: set[str] = set()
                count_yielded = 0
                scroll_attempts = 0
                max_scroll_attempts = max(10, (limit // 5) + 8)

                while count_yielded < limit and scroll_attempts < max_scroll_attempts:
                    if cancel_check and cancel_check():
                        break

                    # Collect candidate links via multiple selector strategies
                    links = await self._find_place_links(page)

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

                            place_id, lat, lon = self.parser.extract_place_id_and_coords(href)
                            if place_id and place_id in seen_place_ids:
                                continue
                            if place_id:
                                seen_place_ids.add(place_id)

                            # Multi-strategy raw card extraction
                            card_parent = await link.evaluate_handle('el => el.closest("div[jsaction]") || el.parentElement')
                            card_text = await card_parent.inner_text() if card_parent else ""
                            card_html = await card_parent.inner_html() if card_parent else ""
                            card_lines = [l.strip() for l in card_text.split("\n") if l.strip()]

                            card_info = self.parser.parse_card_lines(card_lines, default_category=category)
                            aria_name = await link.get_attribute("aria-label")
                            business_name = aria_name or card_info.get("name") or "Unknown"

                            # Detail extraction with multi-strategy fallbacks
                            phone, phone_strat = await self._extract_phone(page, link, card_lines)
                            address, addr_strat = await self._extract_address(page, link, card_info.get("address"))
                            website, web_strat = await self._extract_website(page, link)
                            rating, review_count = await self._extract_metrics(page, card_info)
                            opening_hours = card_info.get("opening_hours")

                            # Store rich raw payload for complete auditability
                            raw_payload = {
                                "query": query,
                                "city": city,
                                "category": category,
                                "card_lines": card_lines[:10],
                                "raw_card_html_sample": card_html[:1500] if card_html else "",
                                "extraction_strategies": {
                                    "phone": phone_strat,
                                    "address": addr_strat,
                                    "website": web_strat,
                                },
                                "aria_label": aria_name,
                            }

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
                                raw_payload=raw_payload,
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
                            await page.evaluate('() => window.scrollBy(0, 1000)')
                            await page.wait_for_timeout(2000)

                        end_text = await page.query_selector('text="You\'ve reached the end of the list"')
                        if end_text:
                            break

            finally:
                await page.close()
                await context.close()
                await browser.close()

    async def _find_place_links(self, page: Page) -> List[ElementHandle]:
        """Finds place links using multi-strategy selectors."""
        # Strategy 1: Maps place canonical links
        links = await page.query_selector_all('a[href*="/maps/place/"]')
        if links:
            return links

        # Strategy 2: Feed container links with aria-label
        links = await page.query_selector_all('div[role="feed"] a[aria-label]')
        if links:
            return links

        # Strategy 3: Broad maps place selector
        return await page.query_selector_all('a[href*="google.com/maps"]')

    async def _extract_phone(
        self,
        page: Page,
        link: ElementHandle,
        card_lines: List[str]
    ) -> tuple[Optional[str], str]:
        """Extracts phone number via button, aria-label, tel: link, or card regex."""
        # Strategy 1: Click card to check detail pane button
        try:
            await link.click(timeout=2500)
            await page.wait_for_timeout(800)

            phone_btn = await page.query_selector('button[data-item-id*="phone"]')
            if phone_btn:
                val = await phone_btn.get_attribute("aria-label")
                phone = self.parser.clean_text_field("phone", val)
                if phone:
                    return phone, "button[data-item-id*='phone']"

            # Strategy 2: aria-label matching
            phone_btn2 = await page.query_selector('button[aria-label*="Phone:"], button[aria-label*="phone:"]')
            if phone_btn2:
                val = await phone_btn2.get_attribute("aria-label")
                phone = self.parser.clean_text_field("phone", val)
                if phone:
                    return phone, "button[aria-label*=phone]"

            # Strategy 3: tel: link
            tel_link = await page.query_selector('a[href^="tel:"]')
            if tel_link:
                href = await tel_link.get_attribute("href")
                if href:
                    return href.replace("tel:", "").strip(), "a[href^='tel:']"
        except Exception:
            pass

        # Strategy 4: Fallback regex in card lines for Indian phone formats
        for line in card_lines:
            m = re.search(r"(?:\+91|0)?[6-9]\d{9}\b", line)
            if m:
                return m.group(0), "card_text_regex"

        return None, "none"

    async def _extract_address(
        self,
        page: Page,
        link: ElementHandle,
        fallback_address: Optional[str]
    ) -> tuple[Optional[str], str]:
        """Extracts full address via data-item-id, aria-label, tooltip, or fallback."""
        try:
            addr_btn = await page.query_selector('button[data-item-id="address"]')
            if addr_btn:
                raw_addr = await addr_btn.get_attribute("aria-label")
                clean = self.parser.clean_text_field("address", raw_addr)
                if clean:
                    return clean, "button[data-item-id='address']"

            addr_btn2 = await page.query_selector('button[aria-label*="Address:"], button[aria-label*="address:"]')
            if addr_btn2:
                raw_addr = await addr_btn2.get_attribute("aria-label")
                clean = self.parser.clean_text_field("address", raw_addr)
                if clean:
                    return clean, "button[aria-label*=address]"
        except Exception:
            pass

        if fallback_address:
            return fallback_address, "card_parsed_fallback"

        return None, "none"

    async def _extract_website(
        self,
        page: Page,
        link: ElementHandle
    ) -> tuple[Optional[str], str]:
        """Extracts website authority link via data-item-id, aria-label, or external link."""
        try:
            web_btn = await page.query_selector('a[data-item-id="authority"]')
            if web_btn:
                href = await web_btn.get_attribute("href")
                if href:
                    return href, "a[data-item-id='authority']"

            web_btn2 = await page.query_selector('a[aria-label*="Website:"], a[aria-label*="website:"]')
            if web_btn2:
                href = await web_btn2.get_attribute("href")
                if href:
                    return href, "a[aria-label*=website]"

            # Strategy 3: Any non-Google external authority link in detail pane
            ext_links = await page.query_selector_all('div[role="main"] a[href^="http"]')
            for el in ext_links:
                h = await el.get_attribute("href")
                if h and not any(d in h for d in ["google.com", "gstatic.com", "googleadservices"]):
                    return h, "external_anchor_heuristic"
        except Exception:
            pass

        return None, "none"

    async def _extract_metrics(
        self,
        page: Page,
        card_info: Dict[str, Any]
    ) -> tuple[Optional[float], Optional[int]]:
        """Extracts rating and review count with multi-strategy fallbacks."""
        rating = card_info.get("rating")
        review_count = card_info.get("review_count")

        if rating is None:
            try:
                rating_el = await page.query_selector('span[aria-label*="stars"], span[aria-label*="star"]')
                if rating_el:
                    r_text = await rating_el.get_attribute("aria-label")
                    r_match = re.search(r"(\d+\.\d+)", r_text or "")
                    if r_match:
                        rating = float(r_match.group(1))
            except Exception:
                pass

        if review_count is None:
            try:
                rev_el = await page.query_selector('button[aria-label*="reviews"]')
                if rev_el:
                    rev_text = await rev_el.get_attribute("aria-label")
                    rev_match = re.search(r"([\d,]+)\s+reviews", rev_text or "")
                    if rev_match:
                        review_count = int(rev_match.group(1).replace(",", ""))
            except Exception:
                pass

        return rating, review_count

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
