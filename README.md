# Ultimate WebScraper MCP

A high-performance, multi-site event scraper MCP server with **site-specific adapters** for Ticketmaster, Eventbrite, Facebook Events, Meetup, Eventful, and generic websites.

## Features

- **🎯 Site-Specific Adapters** - Optimized extraction logic for major event platforms
- **🔄 Hybrid Fetching** - Static HTML first, Playwright fallback for JS-heavy pages
- **📊 Schema.org Support** - Leverages JSON-LD Event structured data
- **🚀 Fallback Parsing** - DOM heuristics for sites without structured data
- **🔌 Plugin Architecture** - Easy to add new site adapters
- **☁️ Modal Ready** - Deploy to Modal with WebSocket support

## Architecture

```
URL → Site Detection → Platform-Specific Adapter → Static HTML
                                                   ↓
                                            JSON-LD Parser
                                                   ↓
                                            (Rich data found?)
                                                   ↓ No
                                            DOM Heuristics
                                                   ↓
                                            (Result good?)
                                                   ↓ No
                                            Playwright (JS)
                                                   ↓
                                            Event Data
```

## Supported Sites

| Site | Adapter | Strategy |
|------|---------|----------|
| **Ticketmaster** | `TicketmasterAdapter` | JSON-LD + DOM patterns |
| **Eventbrite** | `EventbriteAdapter` | JSON-LD + DOM patterns |
| **Facebook Events** | `FacebookEventsAdapter` | OG meta tags |
| **Meetup** | `MeetupAdapter` | JSON-LD + DOM patterns |
| **Eventful** | `EventfulAdapter` | JSON-LD + DOM patterns |
| **Any other site** | Generic Parser | JSON-LD + DOM heuristics |

## Installation & Setup

### Prerequisites

- Python 3.10+
- pip

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# (Optional) Install Playwright for JS rendering
pip install playwright
python -m playwright install chromium
```

### Environment Configuration

Copy `.env` from parent directory or use defaults:

```bash
# Optional - customize if needed
MCP_HOST=0.0.0.0
MCP_PORT=8765
SCRAPER_USER_AGENT=Mozilla/5.0 (compatible; EventScraperMCP/1.0)
SCRAPER_REQUEST_TIMEOUT=15
```

## Usage

### As MCP Server (WebSocket)

```bash
python event_scraper_mcp_server.py
# Server runs on ws://localhost:8765
```

The MCP exposes a single tool:

```json
{
  "tool": "scrapeEventPage",
  "description": "Scrape event details from an event webpage URL",
  "input": {
    "url": "https://www.eventbrite.com/e/conference-2025"
  }
}
```

**Example Response:**

```json
{
  "event": {
    "source_url": "https://www.eventbrite.com/e/conference-2025",
    "title": "Tech Conference 2025",
    "description": "Annual tech conference for developers...",
    "start": "2025-06-15T09:00:00",
    "end": "2025-06-15T17:00:00",
    "location": "San Francisco, CA",
    "price": "199",
    "currency": "USD",
    "organizer": "Tech Events Inc",
    "images": ["https://..."],
    "raw_jsonld": { ... }
  },
  "scrape_method": "eventbrite_adapter"
}
```

### Testing

Run the test suite:

```bash
python test_scraper_local.py
```

Tests include:
- ✓ Adapter detection for each platform
- ✓ Data extraction from adapters
- ✓ Fallback to generic scraper
- ✓ URL pattern matching specificity

## Scrape Method Values

The response includes a `scrape_method` field indicating which strategy was used:

| Method | Description |
|--------|-------------|
| `ticketmaster_adapter` | Ticketmaster-specific extraction |
| `eventbrite_adapter` | Eventbrite-specific extraction |
| `facebook_adapter` | Facebook-specific extraction |
| `meetup_adapter` | Meetup-specific extraction |
| `eventful_adapter` | Eventful-specific extraction |
| `static` | Generic parser (static HTML) |
| `playwright` | Playwright-rendered content |
| `playwright_empty` | Playwright used but result empty |
| `failed` | All methods failed |

## How It Works

### 1. Site Detection

When a URL is provided, the system checks it against known site patterns:

```python
# Example matching
"https://www.ticketmaster.com/event/123" → TicketmasterAdapter
"https://www.eventbrite.com/e/456"        → EventbriteAdapter
"https://www.facebook.com/events/789"     → FacebookEventsAdapter
"https://example.com/event"                → Generic Parser (fallback)
```

### 2. Site-Specific Extraction

Each adapter attempts to extract data using platform-specific patterns:

```python
class TicketmasterAdapter(SiteAdapter):
    def matches(self, url: str) -> bool:
        return "ticketmaster" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        # First try JSON-LD (most reliable)
        event_data = _parse_event_from_jsonld(html, url)
        if event_data:
            return event_data

        # Fall back to DOM patterns specific to Ticketmaster
        # ...
```

### 3. Generic Fallback

If no site adapter matches or extraction fails, the generic parser is used:

1. **JSON-LD Parser** - Looks for schema.org Event JSON-LD markup
2. **DOM Heuristics** - Falls back to OpenGraph tags and HTML patterns
3. **Playwright** - If result looks incomplete, re-fetches with JavaScript rendering

### 4. Quality Check

Results are evaluated on richness:

```python
# Event must have at least 2 of these 3:
- Title
- Start date/time
- Location
```

If result is too sparse, Playwright rendering is attempted.

## Adding New Site Adapters

### Step 1: Create Adapter Class

```python
class MyEventSiteAdapter(SiteAdapter):
    """Adapter for MyEventSite.com events."""

    def matches(self, url: str) -> bool:
        # Return True if this adapter handles the URL
        return "myeventsite.com" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        # Extract event data from HTML
        # Return None if extraction fails (will use generic parser)
        soup = BeautifulSoup(html, "lxml")

        # Your site-specific extraction logic here
        title = soup.find("h1", class_="event-title")

        return {
            "source_url": url,
            "title": title.get_text(strip=True) if title else None,
            "scrape_method": "myeventsite_adapter",
            # ... other fields
        } if title else None
```

### Step 2: Register Adapter

Add to the `SITE_ADAPTERS` list in `event_scraper_mcp_server.py`:

```python
SITE_ADAPTERS = [
    TicketmasterAdapter(),
    EventbriteAdapter(),
    # ... existing adapters ...
    MyEventSiteAdapter(),  # Add your new adapter
]
```

### Step 3: Test It

```python
adapter = get_site_adapter("https://www.myeventsite.com/event/123")
assert isinstance(adapter, MyEventSiteAdapter)
```

## Performance Considerations

### Cold Start Optimization

Playwright is only imported when needed (lazy loading) to keep startup time low:

```python
# Playwright only imported during first dynamic fetch
from playwright.sync_api import sync_playwright
```

### Timeout Strategy

- **Static fetch:** 15 seconds (configurable)
- **Playwright:** 30 seconds
- **Total:** ~45 seconds worst case

### Site-Specific Optimizations

| Site | Optimization |
|------|-------------|
| Ticketmaster | JSON-LD first (reliable) |
| Eventbrite | JSON-LD + meta tags |
| Facebook | OG tags (no JS needed) |
| Meetup | JSON-LD (minimal DOM parsing) |
| Generic | Progressive enhancement |

## Deployment

### Local Testing

```bash
# Terminal 1: Start MCP server
python event_scraper_mcp_server.py

# Terminal 2: Test in Python
python -c "
import requests
url = 'http://localhost:8765'
# (Use WebSocket client for actual MCP communication)
"
```

### Modal Deployment

```bash
# Configure Modal
modal token new

# Deploy
modal deploy modal_app.py

# Get WebSocket URL
# ws://event-scraper-mcp--<hash>.modal.run
```

### Docker Deployment

```bash
docker build -t event-scraper-mcp .
docker run -p 8765:8765 event-scraper-mcp
```

## Troubleshooting

### "Failed to extract event"

1. Check if site is in `SITE_ADAPTERS`
2. Verify site has schema.org markup (`<script type="application/ld+json">`)
3. Try with `--debug` flag to see extraction details

### Slow Performance

1. Likely hitting Playwright fallback (JS-heavy site)
2. Increase `SCRAPER_REQUEST_TIMEOUT` if needed
3. Check network latency to target site

### Playwright Installation Issues

```bash
# Reinstall Playwright and Chromium
pip install --upgrade playwright
python -m playwright install --with-deps chromium
```

## Event Data Structure

```json
{
  "source_url": "string",
  "title": "string",
  "description": "string",
  "start": "ISO 8601 datetime",
  "end": "ISO 8601 datetime",
  "location": "string",
  "raw_location": "object (from JSON-LD)",
  "price": "string or number",
  "currency": "string (ISO 4217)",
  "organizer": "string",
  "status": "string (EventScheduled, EventCancelled, etc)",
  "event_attendance_mode": "string (OfflineEventAttendanceMode, OnlineEventAttendanceMode)",
  "images": ["url", ...],
  "raw_jsonld": "object (full JSON-LD if available)",
  "scrape_method": "string (which method extracted this)"
}
```

## Requirements

- `fastmcp` - MCP framework
- `httpx` - HTTP client
- `beautifulsoup4` - HTML parsing
- `lxml` - XML/HTML parser
- `playwright` - Browser automation (optional, lazy-loaded)
- `python-dotenv` - Environment configuration

## License

MIT

## Contributing

To add support for a new event platform:

1. Create a new adapter class extending `SiteAdapter`
2. Implement `matches()` and `extract_event()` methods
3. Add to `SITE_ADAPTERS` registry
4. Add test cases
5. Submit PR

## Support

For issues or improvements, see the main [MCP Security README](../../../README.md).
