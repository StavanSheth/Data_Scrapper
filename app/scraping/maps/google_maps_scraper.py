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

                            # Detail extraction directly from card container without mutating page state
                            phone, phone_strat = await self._extract_phone(card_parent, card_lines)
                            address, addr_strat = await self._extract_address(card_parent, card_lines, card_info.get("address"))
                            website, web_strat = await self._extract_website(card_parent, link)
                            rating, review_count = await self._extract_metrics(card_parent, card_info)
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

                        except Exception as exc:
                            # A failed record must NEVER be silently discarded
                            logger.warning(
                                "Failed extracting place record at url %s: %s",
                                href if 'href' in locals() else 'unknown',
                                exc,
                                exc_info=True,
                            )
                            count_yielded += 1
                            yield RawGoogleRecord(
                                place_id=place_id if 'place_id' in locals() else None,
                                name=business_name if ('business_name' in locals() and business_name != "Unknown") else "Failed Extraction",
                                category=category,
                                status="EXTRACTION_FAILED",
                                raw_payload={
                                    "error": str(exc),
                                    "profile_url": href if 'href' in locals() else None,
                                    "card_lines": card_lines if 'card_lines' in locals() else [],
                                },
                                profile_url=href if 'href' in locals() else None,
                            )

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
        card_parent: Optional[ElementHandle],
        card_lines: List[str]
    ) -> tuple[Optional[str], str]:
        """Extracts phone number directly from card text lines or card DOM without mutating page state."""
        # Strategy 1: Check card text for Indian phone patterns
        for line in card_lines:
            m = re.search(r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}\b", line)
            if m:
                clean = self.parser.clean_text_field("phone", m.group(0))
                if clean:
                    return clean, "card_text_mobile_regex"
            m_land = re.search(r"\b0\d{2,4}[-\s]?\d{6,8}\b", line)
            if m_land:
                clean = self.parser.clean_text_field("phone", m_land.group(0))
                if clean:
                    return clean, "card_text_landline_regex"

        if card_parent:
            # Strategy 2: Call button or tel: anchor inside the card
            try:
                tel_link = await card_parent.query_selector('a[href^="tel:"]')
                if tel_link:
                    href = await tel_link.get_attribute("href")
                    if href:
                        return self.parser.clean_text_field("phone", href.replace("tel:", "")), "card_tel_link"

                call_btn = await card_parent.query_selector('button[data-tooltip*="Call" i], button[aria-label*="Call" i], button[aria-label*="Phone" i]')
                if call_btn:
                    val = await call_btn.get_attribute("aria-label") or await call_btn.get_attribute("data-tooltip")
                    phone = self.parser.clean_text_field("phone", val)
                    if phone:
                        return phone, "card_call_button"
            except Exception:
                pass

        return None, "none"

    async def _extract_address(
        self,
        card_parent: Optional[ElementHandle],
        card_lines: List[str],
        fallback_address: Optional[str]
    ) -> tuple[Optional[str], str]:
        """Extracts address directly from card metadata without navigating side panes."""
        if fallback_address:
            return fallback_address, "card_parsed_lines"

        # Search in card lines for line containing address cues
        for line in card_lines[1:]:
            if re.search(r"\b(road|rd|marg|street|nagar|floor|complex|plaza|near|opp|behind|sector|block)\b", line, re.IGNORECASE):
                clean = self.parser.clean_text_field("address", line)
                if clean:
                    return clean, "card_text_address_cue"

        return None, "none"

    async def _extract_website(
        self,
        card_parent: Optional[ElementHandle],
        link: ElementHandle
    ) -> tuple[Optional[str], str]:
        """Extracts website authority link directly from card action buttons."""
        if card_parent:
            try:
                web_btn = await card_parent.query_selector('a[data-value="Website"], a[aria-label*="Website" i], a[aria-label*="site" i]')
                if web_btn:
                    href = await web_btn.get_attribute("href")
                    if href and not any(d in href for d in ["google.com", "gstatic.com"]):
                        return href, "card_website_button"

                # Check external anchor on the card
                anchors = await card_parent.query_selector_all('a[href^="http"]')
                for a in anchors:
                    h = await a.get_attribute("href")
                    if h and not any(d in h for d in ["google.com", "gstatic.com", "googleadservices"]):
                        return h, "card_external_anchor"
            except Exception:
                pass

        return None, "none"

    async def _extract_metrics(
        self,
        card_parent: Optional[ElementHandle],
        card_info: Dict[str, Any]
    ) -> tuple[Optional[float], Optional[int]]:
        """Extracts rating and review count from card text and aria labels."""
        rating = card_info.get("rating")
        review_count = card_info.get("review_count")

        if (rating is None or review_count is None) and card_parent:
            try:
                rating_el = await card_parent.query_selector('span[aria-label*="stars" i], span[aria-label*="star" i]')
                if rating_el:
                    r_text = await rating_el.get_attribute("aria-label")
                    r_match = re.search(r"(\d+\.\d+)", r_text or "")
                    if r_match and rating is None:
                        rating = float(r_match.group(1))
                    rev_match = re.search(r"([\d,]+)\s+reviews?", r_text or "", re.IGNORECASE)
                    if rev_match and review_count is None:
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
