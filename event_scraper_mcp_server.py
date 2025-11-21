import os
import json
import time
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastmcp import FastMCP

# Playwright is only imported when needed to keep cold start cheaper
from playwright.sync_api import sync_playwright

load_dotenv()

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8765"))
SCRAPER_USER_AGENT = os.getenv(
    "SCRAPER_USER_AGENT",
    "Mozilla/5.0 (compatible; EventScraperMCP/1.0; +https://example.com/bot)",
)
SCRAPER_REQUEST_TIMEOUT = float(os.getenv("SCRAPER_REQUEST_TIMEOUT", "15"))

app = FastMCP()


# ---------------------------
# Helper utilities
# ---------------------------

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


# ---------------------------
# Site Adapter Plugin System
# ---------------------------

class SiteAdapter(ABC):
    """Base class for site-specific event scrapers."""

    @abstractmethod
    def matches(self, url: str) -> bool:
        """Check if this adapter handles the given URL."""
        pass

    @abstractmethod
    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract event data from HTML. Return None if extraction fails."""
        pass


class TicketmasterAdapter(SiteAdapter):
    """Adapter for Ticketmaster event pages."""

    def matches(self, url: str) -> bool:
        return "ticketmaster" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")

        # Ticketmaster heavily uses JSON-LD
        event_data = _parse_event_from_jsonld(html, url)
        if event_data:
            return event_data

        # Fallback: look for Ticketmaster-specific patterns
        title = None
        h1 = soup.find("h1", class_=re.compile("event.*title", re.I))
        if h1:
            title = h1.get_text(strip=True)

        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = _safe_get_attr(og_title, "content")

        return {
            "source_url": url,
            "title": title,
            "scrape_method": "ticketmaster_adapter",
        } if title else None


class EventbriteAdapter(SiteAdapter):
    """Adapter for Eventbrite event pages."""

    def matches(self, url: str) -> bool:
        return "eventbrite" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")

        # Eventbrite uses JSON-LD and structured data
        event_data = _parse_event_from_jsonld(html, url)
        if event_data:
            return event_data

        # Fallback: Eventbrite-specific DOM patterns
        title = None
        header = soup.find("h1", class_=re.compile("eventTitle", re.I))
        if header:
            title = header.get_text(strip=True)

        if not title:
            meta_title = soup.find("meta", property="og:title")
            if meta_title:
                title = _safe_get_attr(meta_title, "content")

        return {
            "source_url": url,
            "title": title,
            "scrape_method": "eventbrite_adapter",
        } if title else None


class FacebookEventsAdapter(SiteAdapter):
    """Adapter for Facebook Events."""

    def matches(self, url: str) -> bool:
        return "facebook.com" in url.lower() and "events" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")

        # Facebook events use og: meta tags heavily
        og_title = soup.find("meta", property="og:title")
        title = _safe_get_attr(og_title, "content") if og_title else None

        og_desc = soup.find("meta", property="og:description")
        description = _safe_get_attr(og_desc, "content") if og_desc else None

        images = []
        og_image = soup.find("meta", property="og:image")
        if og_image:
            img_url = _safe_get_attr(og_image, "content")
            if img_url:
                images = [img_url]

        return {
            "source_url": url,
            "title": title,
            "description": description,
            "images": images,
            "location": None,
            "start": None,
            "end": None,
            "price": None,
            "currency": None,
            "organizer": None,
            "status": None,
            "event_attendance_mode": None,
            "raw_location": None,
            "raw_jsonld": None,
            "scrape_method": "facebook_adapter",
        } if title else None


class MeetupAdapter(SiteAdapter):
    """Adapter for Meetup.com events."""

    def matches(self, url: str) -> bool:
        url_lower = url.lower()
        return "meetup.com" in url_lower and "/events/" in url_lower

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")

        # Meetup uses JSON-LD
        event_data = _parse_event_from_jsonld(html, url)
        if event_data:
            event_data["scrape_method"] = "meetup_adapter"
            return event_data

        # Fallback: Meetup-specific patterns
        title = None
        title_elem = soup.find("h1", class_=re.compile("eventTitle", re.I))
        if title_elem:
            title = title_elem.get_text(strip=True)

        return {
            "source_url": url,
            "title": title,
            "scrape_method": "meetup_adapter_fallback",
        } if title else None


class EventfulAdapter(SiteAdapter):
    """Adapter for Eventful events."""

    def matches(self, url: str) -> bool:
        return "eventful.com" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")

        # Eventful uses schema.org JSON-LD
        event_data = _parse_event_from_jsonld(html, url)
        if event_data:
            event_data["scrape_method"] = "eventful_adapter"
            return event_data

        # Fallback: look for event title
        og_title = soup.find("meta", property="og:title")
        title = _safe_get_attr(og_title, "content") if og_title else None

        return {
            "source_url": url,
            "title": title,
            "scrape_method": "eventful_adapter_fallback",
        } if title else None


# Registry of all adapters
SITE_ADAPTERS = [
    TicketmasterAdapter(),
    EventbriteAdapter(),
    FacebookEventsAdapter(),
    MeetupAdapter(),
    EventfulAdapter(),
]


def get_site_adapter(url: str) -> Optional[SiteAdapter]:
    """Find and return the appropriate adapter for the given URL."""
    for adapter in SITE_ADAPTERS:
        if adapter.matches(url):
            return adapter
    return None


# ---------------------------
# Utility: HTML -> Event data
# ---------------------------

def _parse_event_from_jsonld(html: str, url: str) -> Optional[Dict[str, Any]]:
    """
    Try to parse schema.org Event from JSON-LD script tags.
    """
    soup = BeautifulSoup(html, "lxml")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue

        candidates = []
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            candidates = [data]

        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            if obj.get("@type") in ("Event", ["Event"]):
                return _normalize_event_from_jsonld(obj, url)

    return None


def _normalize_event_from_jsonld(obj: Dict[str, Any], url: str) -> Dict[str, Any]:
    """
    Normalize a single JSON-LD Event object to our unified schema.
    """
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

    return {
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


def _parse_event_from_dom(html: str, url: str) -> Dict[str, Any]:
    """
    Fallback DOM heuristics when JSON-LD is missing or incomplete.
    """
    soup = BeautifulSoup(html, "lxml")

    # Title heuristic
    title = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)

    # Description heuristic
    desc = None
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        desc = meta_desc["content"].strip()
    if not desc:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            desc = og_desc["content"].strip()

    # Time heuristic: <time> elements with datetime
    start = None
    end = None
    times = soup.find_all("time")
    if times:
        dt_values = [
            t.get("datetime") for t in times if t.get("datetime")
        ]
        if dt_values:
            start = dt_values[0]
            if len(dt_values) > 1:
                end = dt_values[1]

    # Location heuristic: look for elements with 'location' or 'venue' in class/id
    location = None
    candidates = soup.find_all(
        lambda tag: (
            tag.has_attr("class")
            and any("location" in c.lower() or "venue" in c.lower() for c in tag["class"])
        )
        or (tag.has_attr("id") and (
            "location" in tag["id"].lower()
            or "venue" in tag["id"].lower()
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
    images = images[:5]  # cap

    return {
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


def parse_event_html(html: str, url: str) -> Dict[str, Any]:
    """
    Combined parser: prefer JSON-LD Event, then fall back to DOM heuristics.
    """
    event = _parse_event_from_jsonld(html, url)
    if event:
        # Backfill missing fields from DOM heuristics if needed
        dom = _parse_event_from_dom(html, url)
        for key, value in dom.items():
            if event.get(key) in (None, "", []) and value not in (None, "", []):
                event[key] = value
        return event
    else:
        return _parse_event_from_dom(html, url)


# ---------------------------
# Hybrid fetchers
# ---------------------------

def fetch_static_html(url: str) -> Optional[str]:
    """
    Try to fetch HTML with plain HTTP first (fast path).
    """
    try:
        with httpx.Client(
            timeout=SCRAPER_REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": SCRAPER_USER_AGENT},
        ) as client:
            resp = client.get(url)
            if resp.status_code >= 400:
                return None
            text = resp.text
            if text and len(text.strip()) > 0:
                return text
    except Exception as e:
        print(f"[static] Error fetching {url}: {e}")
    return None


def fetch_dynamic_html_with_playwright(url: str) -> Optional[str]:
    """
    Use Playwright (Chromium) to render JS-heavy pages and return full DOM HTML.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=SCRAPER_USER_AGENT)
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Give a little extra time for late JS
            time.sleep(2)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"[playwright] Error fetching {url}: {e}")
        return None


def hybrid_fetch(url: str) -> Dict[str, Any]:
    """
    Full hybrid pipeline with site adapters:
    1. Try site-specific adapter with static HTML
    2. If adapter fails or no adapter, use generic parser with static HTML
    3. If result looks too empty, fallback to Playwright + site adapter/generic parser
    """

    def is_event_rich(ev: Dict[str, Any]) -> bool:
        # Simple heuristic: at least a title and some time OR location.
        if not ev:
            return False
        has_title = bool(ev.get("title"))
        has_time = bool(ev.get("start"))
        has_location = bool(ev.get("location"))
        score = int(has_title) + int(has_time) + int(has_location)
        return score >= 2

    # 1. Try static fetch with site adapter if available
    static_html = fetch_static_html(url)
    static_event = None
    adapter = get_site_adapter(url)

    if static_html:
        if adapter:
            # Use site-specific adapter
            static_event = adapter.extract_event(static_html, url)

        # Fall back to generic parser if adapter failed
        if not static_event:
            static_event = parse_event_html(static_html, url)

    if static_event and is_event_rich(static_event):
        return {
            "event": static_event,
            "scrape_method": static_event.get("scrape_method", "static"),
        }

    # 2. Playwright fallback for JS-heavy content
    dynamic_html = fetch_dynamic_html_with_playwright(url)
    if dynamic_html:
        if adapter:
            # Try adapter again with rendered HTML
            dynamic_event = adapter.extract_event(dynamic_html, url)
        else:
            dynamic_event = None

        # Fall back to generic parser if needed
        if not dynamic_event:
            dynamic_event = parse_event_html(dynamic_html, url)

        return {
            "event": dynamic_event,
            "scrape_method": dynamic_event.get("scrape_method") if dynamic_event else "playwright_empty",
        }

    return {
        "event": static_event or None,
        "scrape_method": "failed",
    }


# ---------------------------
# MCP Tool
# ---------------------------

@app.tool(name="scrapeEventPage", description="Scrape event details from an event webpage URL.")
def scrape_event_page(url: str) -> Dict[str, Any]:
    """
    Hybrid event scraper. Given a URL, tries static HTML first and then
    falls back to Playwright rendering to extract event details.
    """
    result = hybrid_fetch(url)
    return result


# ---------------------------
# MCP WebSocket entrypoint
# ---------------------------

if __name__ == "__main__":
    print(f"Starting Event Scraper MCP server on http://{MCP_HOST}:{MCP_PORT}/mcp")
    app.run(transport="http", host=MCP_HOST, port=MCP_PORT)
