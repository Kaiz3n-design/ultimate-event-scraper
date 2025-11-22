import os
import json
import time
import re
import base64
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8765"))
SCRAPER_USER_AGENT = os.getenv(
    "SCRAPER_USER_AGENT",
    "Mozilla/5.0 (compatible; UltimateEventScraperMCP/1.0; +https://github.com/Kaiz3n-design/ultimate-event-scraper)",
)
SCRAPER_REQUEST_TIMEOUT = float(os.getenv("SCRAPER_REQUEST_TIMEOUT", "15"))


# -------------------------------------------------------------------
# Helper utilities + schema helpers
# -------------------------------------------------------------------

def _safe_get_attr(tag, attr_name: str) -> Optional[str]:
    """Safely get an attribute value from a BeautifulSoup tag and convert to string."""
    if not tag:
        return None
    value = tag.get(attr_name)
    if isinstance(value, list):
        value = " ".join(value)
    if isinstance(value, str):
        return value.strip()
    return None


def ensure_event_shape(ev: Optional[Dict[str, Any]], url: str) -> Dict[str, Any]:
    """
    Ensure event dict has all expected keys with reasonable defaults.
    This keeps the MCP response schema consistent for the LLM.
    """
    base = {
        "source_url": url,
        "title": None,
        "description": None,
        "start": None,
        "end": None,
        "location": None,
        "raw_location": None,
        "price": None,
        "currency": None,
        "organizer": None,
        "status": None,
        "event_attendance_mode": None,
        "images": [],
        "raw_jsonld": None,
        "scrape_method": None,
    }
    if not ev:
        return base
    # Overlay known keys
    for k in base.keys():
        if k in ev and ev[k] is not None:
            base[k] = ev[k]
    # Preserve any extra debug keys
    for k, v in ev.items():
        if k not in base:
            base[k] = v
    return base


def is_event_rich(ev: Optional[Dict[str, Any]]) -> bool:
    """
    Heuristic: a 'rich' event has at least a title AND (start time OR location).
    """
    if not ev or not isinstance(ev, dict):
        return False
    has_title = bool(ev.get("title"))
    has_time = bool(ev.get("start"))
    has_location = bool(ev.get("location"))
    score = int(has_title) + int(has_time) + int(has_location)
    return score >= 2


# -------------------------------------------------------------------
# Site Adapter Plugin System
# -------------------------------------------------------------------

class SiteAdapter(ABC):
    """Base class for site-specific event scrapers."""

    @abstractmethod
    def matches(self, url: str) -> bool:
        """Check if this adapter handles the given URL."""
        ...

    @abstractmethod
    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract event data from HTML.
        Should return a full, normalized event dict or None if it can't handle it.
        """
        ...


class TicketmasterAdapter(SiteAdapter):
    """Adapter for Ticketmaster event pages."""

    def matches(self, url: str) -> bool:
        return "ticketmaster" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        base = parse_event_html(html, url)
        base["scrape_method"] = "ticketmaster_adapter"

        # Optional: override title with more specific selector if available
        soup = BeautifulSoup(html, "lxml")
        h1 = soup.find("h1", class_=re.compile("event.*title", re.I))
        if h1 and h1.get_text(strip=True):
            base["title"] = h1.get_text(strip=True)

        base = ensure_event_shape(base, url)
        return base if is_event_rich(base) else None


class EventbriteAdapter(SiteAdapter):
    """Adapter for Eventbrite event pages."""

    def matches(self, url: str) -> bool:
        return "eventbrite" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        base = parse_event_html(html, url)
        base["scrape_method"] = "eventbrite_adapter"

        soup = BeautifulSoup(html, "lxml")
        header = soup.find("h1", class_=re.compile("eventTitle", re.I))
        if header and header.get_text(strip=True):
            base["title"] = header.get_text(strip=True)

        base = ensure_event_shape(base, url)
        return base if is_event_rich(base) else None


class FacebookEventsAdapter(SiteAdapter):
    """Adapter for Facebook Events."""

    def matches(self, url: str) -> bool:
        return "facebook.com" in url.lower() and "events" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")

        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")

        base = ensure_event_shape(None, url)
        base["title"] = _safe_get_attr(og_title, "content")
        base["description"] = _safe_get_attr(og_desc, "content")

        images = []
        if og_image:
            img_url = _safe_get_attr(og_image, "content")
            if img_url:
                images.append(img_url)
        base["images"] = images
        base["scrape_method"] = "facebook_adapter"

        return base if is_event_rich(base) else None


class MeetupAdapter(SiteAdapter):
    """Adapter for Meetup.com events."""

    def matches(self, url: str) -> bool:
        url_lower = url.lower()
        return "meetup.com" in url_lower and "/events/" in url_lower

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        base = parse_event_html(html, url)
        base["scrape_method"] = "meetup_adapter"
        base = ensure_event_shape(base, url)
        return base if is_event_rich(base) else None


class EventfulAdapter(SiteAdapter):
    """Adapter for Eventful events."""

    def matches(self, url: str) -> bool:
        return "eventful.com" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        base = parse_event_html(html, url)
        base["scrape_method"] = "eventful_adapter"
        base = ensure_event_shape(base, url)
        return base if is_event_rich(base) else None


SITE_ADAPTERS = [
    TicketmasterAdapter(),
    EventbriteAdapter(),
    FacebookEventsAdapter(),
    MeetupAdapter(),
    EventfulAdapter(),
]


def get_site_adapter(url: str) -> Optional[SiteAdapter]:
    for adapter in SITE_ADAPTERS:
        if adapter.matches(url):
            return adapter
    return None


# -------------------------------------------------------------------
# HTML → Event parsing
# -------------------------------------------------------------------

def _parse_event_from_jsonld(html: str, url: str) -> Optional[Dict[str, Any]]:
    """Try to parse schema.org Event from JSON-LD script tags."""
    soup = BeautifulSoup(html, "lxml")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue

        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            candidates = [data]
        else:
            continue

        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            if obj.get("@type") in ("Event", ["Event"]):
                return _normalize_event_from_jsonld(obj, url)

    return None


def _normalize_event_from_jsonld(obj: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Normalize a single JSON-LD Event object to our unified schema."""

    def safe_get(*keys, default=None):
        cur = obj
        for k in keys:
            if isinstance(cur, dict):
                cur = cur.get(k)
            else:
                return default
        return cur if cur is not None else default

    # Location
    loc = safe_get("location", default={})
    location_name = None
    address_str = None
    if isinstance(loc, dict):
        location_name = loc.get("name") or loc.get("@name")
        addr = loc.get("address")
        if isinstance(addr, dict):
            parts = [
                addr.get("streetAddress"),
                addr.get("addressLocality"),
                addr.get("addressRegion"),
                addr.get("postalCode"),
                addr.get("addressCountry"),
            ]
            address_str = ", ".join([p for p in parts if p])
        elif isinstance(addr, str):
            address_str = addr

    location_combined = ", ".join(
        [p for p in [location_name, address_str] if p]
    ) or None

    # Offers / price
    offers = obj.get("offers")
    price = None
    currency = None
    if isinstance(offers, dict):
        price = offers.get("price")
        currency = offers.get("priceCurrency")

    organizer_obj = obj.get("organizer")
    organizer_name = None
    if isinstance(organizer_obj, dict):
        organizer_name = organizer_obj.get("name")
    elif isinstance(organizer_obj, str):
        organizer_name = organizer_obj

    images = []
    img = obj.get("image")
    if isinstance(img, str):
        images = [img]
    elif isinstance(img, list):
        images = [i for i in img if isinstance(i, str)]

    event = {
        "source_url": url,
        "title": obj.get("name"),
        "description": obj.get("description"),
        "start": obj.get("startDate"),
        "end": obj.get("endDate"),
        "location": location_combined,
        "raw_location": loc,
        "price": price,
        "currency": currency,
        "organizer": organizer_name,
        "status": obj.get("eventStatus"),
        "event_attendance_mode": obj.get("eventAttendanceMode"),
        "images": images,
        "raw_jsonld": obj,
    }
    return ensure_event_shape(event, url)


def _parse_event_from_dom(html: str, url: str) -> Dict[str, Any]:
    """Fallback DOM heuristics when JSON-LD is missing or incomplete."""
    soup = BeautifulSoup(html, "lxml")

    # Title heuristic
    title = None
    og_title = soup.find("meta", property="og:title")
    if og_title:
        title = _safe_get_attr(og_title, "content")
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)

    # Description
    desc = None
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        content = _safe_get_attr(meta_desc, "content")
        if content:
            desc = content
    if not desc:
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            content = _safe_get_attr(og_desc, "content")
            if content:
                desc = content

    # Time: <time datetime="...">
    start = None
    end = None
    times = soup.find_all("time")
    if times:
        dt_values = [t.get("datetime") for t in times if t.get("datetime")]
        if dt_values:
            start = dt_values[0]
            if len(dt_values) > 1:
                end = dt_values[1]

    # Location heuristic
    location = None
    candidates = soup.find_all(
        lambda tag: (
            tag.has_attr("class")
            and any("location" in c.lower() or "venue" in c.lower() for c in tag["class"])
        )
        or (tag.has_attr("id") and (
            "location" in str(tag["id"]).lower()
            or "venue" in str(tag["id"]).lower()
        ))
    )
    for c in candidates:
        text = c.get_text(" ", strip=True)
        if text and len(text) > 3:
            location = text
            break

    # Images
    images = []
    for img in soup.find_all("meta", property="og:image"):
        if img.get("content"):
            images.append(img["content"])
    if not images:
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src")
            if src:
                images.append(src)
    images = images[:5]

    event = {
        "source_url": url,
        "title": title,
        "description": desc,
        "start": start,
        "end": end,
        "location": location,
        "raw_location": None,
        "price": None,
        "currency": None,
        "organizer": None,
        "status": None,
        "event_attendance_mode": None,
        "images": images,
        "raw_jsonld": None,
    }
    return ensure_event_shape(event, url)


def parse_event_html(html: str, url: str) -> Dict[str, Any]:
    """Combined parser: prefer JSON-LD Event, then fall back to DOM heuristics."""
    event = _parse_event_from_jsonld(html, url)
    if event:
        dom = _parse_event_from_dom(html, url)
        for key, value in dom.items():
            if event.get(key) in (None, "", []) and value not in (None, "", []):
                event[key] = value
        return ensure_event_shape(event, url)
    else:
        return _parse_event_from_dom(html, url)


# -------------------------------------------------------------------
# Hybrid fetching (static + Playwright)
# -------------------------------------------------------------------

def fetch_static_html(url: str) -> Optional[str]:
    """Try to fetch HTML with plain HTTP first (fast path)."""
    try:
        with httpx.Client(
            timeout=SCRAPER_REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": SCRAPER_USER_AGENT},
        ) as client:
            resp = client.get(url)
            if resp.status_code >= 400:
                print(f"[static] HTTP {resp.status_code} for {url}")
                return None
            text = resp.text
            return text if text and text.strip() else None
    except Exception as e:
        print(f"[static] Error fetching {url}: {e}")
    return None


async def fetch_dynamic_html_with_playwright(url: str) -> Optional[str]:
    """
    Use Playwright (Chromium) to render JS-heavy pages and return full DOM HTML.
    Imported lazily to keep cold start cheaper.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=SCRAPER_USER_AGENT)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)  # grace period for late JS
            html = await page.content()
            await browser.close()
            return html
    except Exception as e:
        print(f"[playwright] Error fetching {url}: {e}")
        return None


async def hybrid_fetch(url: str) -> Dict[str, Any]:
    """
    Full hybrid pipeline with site adapters:
      1. Try site-specific adapter with static HTML.
      2. If adapter fails or no adapter, use generic parser with static HTML.
      3. If result is not rich, fallback to Playwright + site adapter/generic parser.
    """
    adapter = get_site_adapter(url)

    # 1) Static first
    static_html = fetch_static_html(url)
    static_event = None

    if static_html:
        if adapter:
            static_event = adapter.extract_event(static_html, url)

        # fallback to generic parser if no adapter or adapter result not rich
        if not static_event or not is_event_rich(static_event):
            generic = parse_event_html(static_html, url)
            if static_event:
                # backfill adapter result with generic fields
                for k, v in generic.items():
                    if static_event.get(k) in (None, "", []) and v not in (None, "", []):
                        static_event[k] = v
            else:
                static_event = generic

    static_event = ensure_event_shape(static_event, url) if static_event else None

    if static_event and is_event_rich(static_event):
        if not static_event.get("scrape_method"):
            static_event["scrape_method"] = "static"
        return {
            "event": static_event,
            "scrape_method": static_event["scrape_method"],
        }

    # 2) Playwright fallback
    dynamic_html = await fetch_dynamic_html_with_playwright(url)
    dynamic_event = None

    if dynamic_html:
        if adapter:
            dynamic_event = adapter.extract_event(dynamic_html, url)

        if not dynamic_event or not is_event_rich(dynamic_event):
            generic_dyn = parse_event_html(dynamic_html, url)
            if dynamic_event:
                for k, v in generic_dyn.items():
                    if dynamic_event.get(k) in (None, "", []) and v not in (None, "", []):
                        dynamic_event[k] = v
            else:
                dynamic_event = generic_dyn

    dynamic_event = ensure_event_shape(dynamic_event, url) if dynamic_event else None

    if dynamic_event and is_event_rich(dynamic_event):
        if not dynamic_event.get("scrape_method"):
            dynamic_event["scrape_method"] = "playwright"
        return {
            "event": dynamic_event,
            "scrape_method": dynamic_event["scrape_method"],
        }

    # 3) Total failure: return best-effort + error field
    best = dynamic_event or static_event
    best = ensure_event_shape(best, url) if best else ensure_event_shape(None, url)
    best["scrape_method"] = "failed"
    return {
        "event": best,
        "scrape_method": "failed",
        "error": "Could not extract a rich event; check the URL or page structure.",
    }


# -------------------------------------------------------------------
# Screenshot, PDF, Media, and Advanced Features
# -------------------------------------------------------------------

async def capture_event_screenshot(url: str) -> Optional[Dict[str, Any]]:
    """
    Capture a screenshot of the event page using Playwright.
    Returns base64-encoded PNG for embedding in responses.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=SCRAPER_USER_AGENT)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)  # Grace period for rendering
            screenshot_bytes = await page.screenshot(type="png")
            await browser.close()

            # Encode to base64 for transport
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            return {
                "url": url,
                "screenshot_base64": screenshot_b64,
                "format": "png",
            }
    except Exception as e:
        print(f"[screenshot] Error capturing screenshot for {url}: {e}")
        return {"url": url, "error": str(e)}


async def generate_event_pdf(url: str) -> Optional[Dict[str, Any]]:
    """
    Generate a PDF brochure of the event page using Playwright.
    Returns base64-encoded PDF.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=SCRAPER_USER_AGENT)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)
            pdf_bytes = await page.pdf(format="A4")
            await browser.close()

            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            return {
                "url": url,
                "pdf_base64": pdf_b64,
                "format": "pdf",
            }
    except Exception as e:
        print(f"[pdf] Error generating PDF for {url}: {e}")
        return {"url": url, "error": str(e)}


def extract_event_media(html: str, url: str) -> Dict[str, Any]:
    """
    Extract all media (images, videos) from the event page.
    """
    soup = BeautifulSoup(html, "lxml")

    images = []
    videos = []

    # Extract images
    for img in soup.find_all("img"):
        src = img.get("src")
        alt = img.get("alt", "")
        if src:
            images.append({"url": src, "alt": alt})

    # Extract video sources
    for video in soup.find_all("video"):
        for source in video.find_all("source"):
            src = source.get("src")
            video_type = source.get("type", "")
            if src:
                videos.append({"url": src, "type": video_type})

    # Extract YouTube embeds from iframes
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if src and ("youtube.com" in src or "youtu.be" in src):
            videos.append({"url": src, "type": "youtube"})

    # Extract from og:image meta tags
    for meta in soup.find_all("meta", property="og:image"):
        content = meta.get("content")
        if content:
            images.append({"url": content, "source": "og:image"})

    return {
        "url": url,
        "images": images[:20],  # Limit to first 20
        "videos": videos[:10],  # Limit to first 10
        "total_images": len(images),
        "total_videos": len(videos),
    }


async def check_ticket_availability(url: str) -> Dict[str, Any]:
    """
    Check ticket availability and pricing information from event page.
    Uses Playwright to handle dynamic content.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=SCRAPER_USER_AGENT)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)  # Wait for JS to render prices/availability

            # Execute JavaScript to check for ticket/button states
            ticket_info = await page.evaluate(
                """
                () => {
                    const info = {
                        has_register_button: !!document.querySelector('[onclick*="register"], button[aria-label*="register"], button:contains("Register")'),
                        has_buy_button: !!document.querySelector('a[href*="tickets"], button:contains("Buy"), button:contains("Get Tickets")'),
                        has_sold_out: !!document.body.innerText.match(/sold[\\s-]*out|no[\\s-]*tickets|unavailable/i),
                        price_text: (document.body.innerText.match(/\\$[\\d,]+\\.?\\d*|free|complimentary/i) || ['N/A'])[0],
                        form_inputs: Array.from(document.querySelectorAll('input[type="email"], input[type="text"], input[placeholder*="email"], input[placeholder*="name"]')).length,
                    };
                    return info;
                }
                """
            )

            await browser.close()

            return {
                "url": url,
                "ticket_info": ticket_info,
                "status": "sold_out" if ticket_info["has_sold_out"] else "available",
            }
    except Exception as e:
        print(f"[availability] Error checking availability for {url}: {e}")
        return {"url": url, "error": str(e)}
    
async def search_event_listings(
    url: str, location_filter: Optional[str] = None, keyword_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search event listings on a page using Playwright for dynamic rendering.
    Filters results by location and/or keyword using Playwright locators.

    Args:
        url: URL of the event listing page (e.g., eventbrite.com/d/location/events/)
        location_filter: Optional location to filter by (e.g., "Memphis")
        keyword_filter: Optional keyword to filter by (e.g., "concert", "sports")

    Returns:
        Dict with matched events list and metadata
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=SCRAPER_USER_AGENT)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)  # Wait for event cards to fully render

            # Selectors for common event listing pages
            event_selectors = [
                "[data-testid='event-card']",  # Eventbrite
                "[class*='event-card']",
                "[class*='event-item']",
                "article[class*='event']",
                "div[role='listitem']",
            ]

            event_locator = None
            for selector in event_selectors:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        event_locator = page.locator(selector)
                        print(f"[search_events] Found {count} events using selector: {selector}")
                        break
                except Exception:
                    continue

            if not event_locator:
                return {
                    "url": url,
                    "events": [],
                    "error": "Could not find event cards on page",
                }

            # Apply filters
            if location_filter:
                event_locator = event_locator.filter(has_text=location_filter)
            if keyword_filter:
                event_locator = event_locator.filter(has_text=keyword_filter)

            event_count = await event_locator.count()
            events = []

            # Extract details from each matching event (limit to 20)
            for i in range(min(event_count, 20)):
                try:
                    event_element = event_locator.nth(i)
                    event_data: Dict[str, Any] = {"position": i + 1}

                    # Try to extract title
                    title_selectors = ["h3", "h2", "[class*='title']", "a[class*='event-link']"]
                    for title_sel in title_selectors:
                        try:
                            title = await event_element.locator(title_sel).first.inner_text()
                            if title:
                                event_data["title"] = title.strip()
                                break
                        except Exception:
                            continue

                    # Try to extract date
                    time_selectors = ["[class*='date']", "[class*='time']", "time"]
                    for time_sel in time_selectors:
                        try:
                            date_text = await event_element.locator(time_sel).first.inner_text()
                            if date_text:
                                event_data["date"] = date_text.strip()
                                break
                        except Exception:
                            continue

                    # Try to extract location
                    location_selectors = ["[class*='location']", "[class*='venue']", "span[class*='address']"]
                    for loc_sel in location_selectors:
                        try:
                            location_text = await event_element.locator(loc_sel).first.inner_text()
                            if location_text:
                                event_data["location"] = location_text.strip()
                                break
                        except Exception:
                            continue

                    # Try to extract price
                    price_selectors = ["[class*='price']", "[class*='cost']"]
                    for price_sel in price_selectors:
                        try:
                            price_text = await event_element.locator(price_sel).first.inner_text()
                            if price_text:
                                event_data["price"] = price_text.strip()
                                break
                        except Exception:
                            continue

                    # Try to extract event URL
                    try:
                        link = await event_element.locator("a").first.get_attribute("href")
                        if link:
                            event_data["url"] = link if link.startswith("http") else urljoin(url, link)
                    except Exception:
                        pass

                    if event_data:
                        events.append(event_data)

                except Exception:
                    continue

            await browser.close()

            return {
                "url": url,
                "events": events,
                "total_found": event_count,
                "total_returned": len(events),
                "filters_applied": {
                    "location": location_filter,
                    "keyword": keyword_filter,
                },
            }

    except Exception as e:
        print(f"[search_events] Error: {e}")
        return {
            "url": url,
            "events": [],
            "error": str(e),
        }

def generate_ics_calendar(event_data: Dict[str, Any]) -> Optional[str]:
    """
    Generate an ICS (iCalendar) file from event data.
    Returns ICS content as string.
    """
    try:
        title = (event_data.get("title") or "Event").replace("\n", " ")
        start = event_data.get("start")
        end = event_data.get("end")
        location = (event_data.get("location") or "").replace("\n", " ")
        description = (event_data.get("description") or "").replace("\n", "\\n")
        url = event_data.get("source_url", "")

        # Basic ICS format (simplified, no timezone conversion)
        ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Event Scraper MCP//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{url}
DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{start if start else 'N/A'}
DTEND:{end if end else 'N/A'}
SUMMARY:{title}
DESCRIPTION:{description}
LOCATION:{location}
URL:{url}
END:VEVENT
END:VCALENDAR"""

        return ics
    except Exception as e:
        print(f"[ics] Error generating ICS: {e}")
        return None


# -------------------------------------------------------------------
# FastMCP server + tool
# -------------------------------------------------------------------

def make_mcp_server() -> FastMCP:
    """
    Factory that creates the FastMCP server.
    This matches the pattern in the Modal example:
    mcp = make_mcp_server()
    mcp_app = mcp.http_app(transport="streamable-http", stateless_http=True)
    """
    mcp = FastMCP(
        name="Ultimate Event Scraper MCP",
        instructions=(
            "A server that scrapes event details. "
            "IMPORTANT: If scrapeEventPage fails, automatically use "
            "scrapeEventPageWithFallbacks instead. If searchEventListings "
            "fails, use searchEventListingsWithRetry or any of the tools that use fallbacks."
            "If all else fails try other tools. If still no success, return an error message."
        ),
    )

    @mcp.tool()
    async def scrapeEventPage(url: str) -> Dict[str, Any]:
        """
        Scrape event details from an event webpage URL.
        Returns a consistent JSON object with fields like title, start, end, location, etc.
        """
        try:
            return await hybrid_fetch(url)
        except Exception as e:
            print(f"[scrapeEventPage] Unexpected error for {url}: {e}")
            return {
                "event": ensure_event_shape(None, url),
                "scrape_method": "error",
                "error": str(e),
            }

    @mcp.tool()
    async def scrapeEventPageWithFallbacks(url: str) -> Dict[str, Any]:
        """
        Scrape event details with intelligent fallback strategies.
        Tries multiple scraping methods in sequence to extract event data:
        1. Primary: hybrid_fetch (static HTML → Playwright rendering)
        2. Secondary: checkTicketAvailability (extract from ticket/pricing info)
        3. Tertiary: captureEventScreenshot with metadata

        Returns the best result found across all strategies.
        """
        attempt_log = []

        # Strategy 1: Primary hybrid fetch
        try:
            print(f"[scrapeEventPageWithFallbacks] Attempting hybrid fetch for {url}")
            result = await hybrid_fetch(url)
            if result and result.get("event") and is_event_rich(result.get("event")):
                result["attempts"] = attempt_log + ["hybrid_fetch (SUCCESS)"]
                return result
            attempt_log.append("hybrid_fetch (returned incomplete data)")
        except Exception as e:
            attempt_log.append(f"hybrid_fetch (failed: {str(e)[:50]})")
            print(f"[scrapeEventPageWithFallbacks] Hybrid fetch failed: {e}")

        # Strategy 2: Fallback to ticket availability (can reveal pricing/event details)
        try:
            print(f"[scrapeEventPageWithFallbacks] Attempting ticket availability check for {url}")
            ticket_result = await check_ticket_availability(url)
            if ticket_result and ticket_result.get("url"):
                # Enrich the previous incomplete result with ticket data
                event = ensure_event_shape(None, url)
                if ticket_result.get("has_tickets"):
                    event["status"] = "has_tickets"
                if ticket_result.get("pricing"):
                    event["price"] = ticket_result.get("pricing")
                if ticket_result.get("ticket_info"):
                    event["description"] = ticket_result.get("ticket_info")
                attempt_log.append("checkTicketAvailability (extracted partial data)")
                return {
                    "event": event,
                    "scrape_method": "fallback_ticket_check",
                    "attempts": attempt_log,
                }
        except Exception as e:
            attempt_log.append(f"checkTicketAvailability (failed: {str(e)[:50]})")
            print(f"[scrapeEventPageWithFallbacks] Ticket check failed: {e}")

        # Strategy 3: Screenshot capture (visual validation, metadata preserved)
        try:
            print(f"[scrapeEventPageWithFallbacks] Attempting screenshot capture for {url}")
            screenshot_result = await capture_event_screenshot(url)
            if screenshot_result and not screenshot_result.get("error"):
                # Screenshot succeeded; create minimal event object
                event = ensure_event_shape(None, url)
                attempt_log.append("captureEventScreenshot (visual capture succeeded)")
                return {
                    "event": event,
                    "scrape_method": "fallback_screenshot",
                    "screenshot_data": screenshot_result,
                    "note": "Unable to extract text data, but screenshot captured for manual review",
                    "attempts": attempt_log,
                }
        except Exception as e:
            attempt_log.append(f"captureEventScreenshot (failed: {str(e)[:50]})")
            print(f"[scrapeEventPageWithFallbacks] Screenshot failed: {e}")

        # All strategies failed
        attempt_log.append("all_strategies_exhausted")
        print(f"[scrapeEventPageWithFallbacks] All fallback strategies exhausted for {url}")
        return {
            "event": ensure_event_shape(None, url),
            "scrape_method": "all_fallbacks_failed",
            "error": "Could not extract event data using any available strategy",
            "attempts": attempt_log,
        }

    @mcp.tool()
    async def captureEventScreenshot(url: str) -> Dict[str, Any]:
        """
        Capture a screenshot of the event page for visual preview.
        Returns base64-encoded PNG image data.
        """
        try:
            result = await capture_event_screenshot(url)
            return result or {"url": url, "error": "Screenshot capture failed"}
        except Exception as e:
            print(f"[captureEventScreenshot] Error for {url}: {e}")
            return {"url": url, "error": str(e)}

    @mcp.tool()
    async def generateEventPDF(url: str) -> Dict[str, Any]:
        """
        Generate a PDF brochure of the event page.
        Returns base64-encoded PDF data.
        """
        try:
            result = await generate_event_pdf(url)
            return result or {"url": url, "error": "PDF generation failed"}
        except Exception as e:
            print(f"[generateEventPDF] Error for {url}: {e}")
            return {"url": url, "error": str(e)}

    @mcp.tool()
    async def extractEventMedia(url: str) -> Dict[str, Any]:
        """
        Extract all media (images, videos) from the event page.
        Returns lists of image and video URLs found on the page.
        """
        try:
            # Fetch HTML first
            html = fetch_static_html(url) or await fetch_dynamic_html_with_playwright(url)
            if not html:
                return {"url": url, "error": "Could not fetch page content"}
            return extract_event_media(html, url)
        except Exception as e:
            print(f"[extractEventMedia] Error for {url}: {e}")
            return {"url": url, "error": str(e)}

    @mcp.tool()
    async def checkTicketAvailability(url: str) -> Dict[str, Any]:
        """
        Check ticket availability and pricing information.
        Detects buy buttons, sold-out status, and pricing information.
        """
        try:
            return await check_ticket_availability(url)
        except Exception as e:
            print(f"[checkTicketAvailability] Error for {url}: {e}")
            return {"url": url, "error": str(e)}
        
    @mcp.tool()
    async def searchEventListings(
        url: str, location_filter: Optional[str] = None, keyword_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search and filter events on a listing page using Playwright.
        Automatically detects event cards and extracts their details.

        Args:
            url: URL of the event listing page (e.g., eventbrite.com/d/location/events/)
            location_filter: Optional location to filter by (e.g., "Memphis")
            keyword_filter: Optional keyword to filter by (e.g., "concert", "sports")

        Returns:
            List of matched events with title, date, location, price, and URL.
        """
        try:
            return await search_event_listings(url, location_filter, keyword_filter)
        except Exception as e:
            print(f"[searchEventListings] Error for {url}: {e}")
            return {"url": url, "events": [], "error": str(e)}

    @mcp.tool()
    async def searchEventListingsWithRetry(
        url: str, location_filter: Optional[str] = None, keyword_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search events with intelligent retry logic.
        Handles edge cases like invalid URLs, pages without listing sections, and empty results.

        Retry strategies:
        1. Primary: Direct search on the provided URL
        2. Secondary: Remove filters and try again (if filters were provided)
        3. Tertiary: Try the domain root if listing page detection fails
        4. Fallback: Suggest alternative URLs for known event platforms

        Args:
            url: URL of the event listing page (e.g., eventbrite.com/d/location/events/)
            location_filter: Optional location to filter by (e.g., "Memphis")
            keyword_filter: Optional keyword to filter by (e.g., "concert", "sports")

        Returns:
            List of matched events with metadata about retry strategies used.
        """
        attempts = []

        # Strategy 1: Try with provided URL and filters
        try:
            print(f"[searchEventListingsWithRetry] Attempt 1: Search with filters on {url}")
            result = await search_event_listings(url, location_filter, keyword_filter)
            events = result.get("events", [])
            error = result.get("error")

            if events:
                attempts.append("Primary search with filters (SUCCESS)")
                result["retry_attempts"] = attempts
                result["strategy"] = "primary"
                return result

            # Events found but empty - try without filters
            if not events and (location_filter or keyword_filter):
                attempts.append("Primary search with filters (no results, retrying without filters)")
            else:
                attempts.append(f"Primary search failed: {error or 'no events found'}")
        except Exception as e:
            attempts.append(f"Primary search failed: {str(e)[:60]}")
            print(f"[searchEventListingsWithRetry] Strategy 1 failed: {e}")

        # Strategy 2: Retry without filters (if filters were provided)
        if location_filter or keyword_filter:
            try:
                print(f"[searchEventListingsWithRetry] Attempt 2: Search without filters on {url}")
                result = await search_event_listings(url, location_filter=None, keyword_filter=None)
                events = result.get("events", [])

                if events:
                    attempts.append("Retry without filters (SUCCESS)")
                    result["retry_attempts"] = attempts
                    result["strategy"] = "retry_no_filters"
                    result["note"] = f"Could not apply filters ({location_filter}, {keyword_filter}). Showing all events."
                    return result

                attempts.append(f"Retry without filters (returned {len(events)} events)")
            except Exception as e:
                attempts.append(f"Retry without filters failed: {str(e)[:60]}")
                print(f"[searchEventListingsWithRetry] Strategy 2 failed: {e}")

        # Strategy 3: Try domain root for known platforms
        if any(platform in url.lower() for platform in ["eventbrite.com", "ticketmaster.com", "meetup.com"]):
            try:
                # Extract domain and suggest listing path
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = f"{parsed.scheme}://{parsed.netloc}"

                # Try common listing paths
                listing_paths = [
                    "/d/online/events/",
                    "/d/united-states/events/",
                    "/search/",
                    "/events/",
                ]

                for path in listing_paths:
                    fallback_url = domain + path
                    print(f"[searchEventListingsWithRetry] Attempt 3: Trying fallback URL {fallback_url}")
                    try:
                        result = await search_event_listings(fallback_url, location_filter=None, keyword_filter=None)
                        events = result.get("events", [])
                        if events:
                            attempts.append(f"Fallback URL succeeded: {fallback_url}")
                            result["retry_attempts"] = attempts
                            result["strategy"] = "fallback_url"
                            result["original_url"] = url
                            result["fallback_url"] = fallback_url
                            return result
                    except Exception:
                        continue

                attempts.append("All fallback URLs returned no events")
            except Exception as e:
                attempts.append(f"Fallback URL strategy failed: {str(e)[:60]}")
                print(f"[searchEventListingsWithRetry] Strategy 3 failed: {e}")

        # All strategies exhausted
        attempts.append("all_retry_strategies_exhausted")
        print(f"[searchEventListingsWithRetry] All retry strategies exhausted for {url}")

        return {
            "url": url,
            "events": [],
            "retry_attempts": attempts,
            "strategy": "all_failed",
            "error": "Could not find event listings using any retry strategy",
            "suggestions": [
                "Verify the URL is a valid event listing page (not homepage)",
                "Try a URL like: eventbrite.com/d/your-location/events/",
                "Check that the event platform is supported (Eventbrite, Ticketmaster, Meetup, etc.)",
            ],
        }   

    @mcp.tool()
    async def generateEventCalendar(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an ICS (iCalendar) file from event data.
        Can be imported into calendar applications.
        Requires event_data with fields like title, start, end, location, description.
        """
        try:
            ics_content = generate_ics_calendar(event_data)
            if ics_content:
                return {
                    "ics_content": ics_content,
                    "format": "ics",
                    "success": True,
                }
            else:
                return {"error": "Failed to generate ICS content"}
        except Exception as e:
            print(f"[generateEventCalendar] Error: {e}")
            return {"error": str(e)}

    return mcp


# For local testing only (not used on Modal's stateless HTTP deployment)
if __name__ == "__main__":
    mcp = make_mcp_server()
    print(f"Starting Event Scraper MCP server on http://{MCP_HOST}:{MCP_PORT}/mcp")
    # You can choose "http" or "streamable-http" here; for MCP inspector,
    # "streamable-http" is generally what you'll want.
    mcp.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT)
