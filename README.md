# Ultimate Event Scraper MCP

A powerful Model Context Protocol (MCP) server for comprehensive event data extraction, featuring multi-site support with site-specific adapters, advanced media handling, and intelligent content analysis.

## Features

- **📄 Event Data Extraction** - Extract comprehensive event details from any event webpage
- **🖼️ Screenshot & PDF Generation** - Capture visual representations of event pages
- **🎬 Media Extraction** - Pull images, videos, and media assets from event pages
- **🎫 Ticket Availability Checking** - Real-time ticket availability and pricing detection
- **📅 Calendar Integration** - Generate ICS files for importing into calendar applications
- **🎯 Site-Specific Adapters** - Optimized extraction for Ticketmaster, Eventbrite, Facebook Events, Meetup, and Eventful
- **🔄 Hybrid Fetching** - Static HTML parsing + Playwright fallback for JavaScript-heavy pages
- **📊 Schema.org Support** - Leverages JSON-LD Event structured data
- **🔌 Plugin Architecture** - Extensible adapter system for new platforms
- **☁️ Serverless Ready** - Deploy to Modal.com or run locally

## Architecture

### Request Flow

```
User Input (URL/Event Page)
    ↓
Site Detection (Ticketmaster? Eventbrite? etc.)
    ↓
Platform-Specific Adapter (if available)
    ↓
Fetch Static HTML (httpx, 15s timeout)
    ↓
Parse JSON-LD Schema.org Data
    ↓
Quality Check (Has title + date + location?)
    ↓ No - Try DOM Heuristics
    ↓ Still No - Launch Playwright
    ↓
Return Event Data (with scrape_method indicator)
```

### Component Overview

| Component | Purpose |
|-----------|---------|
| **SiteAdapter** | Abstract base for platform-specific extraction |
| **TicketmasterAdapter** | Ticketmaster event extraction logic |
| **EventbriteAdapter** | Eventbrite event extraction logic |
| **FacebookEventsAdapter** | Facebook Events metadata extraction |
| **MeetupAdapter** | Meetup.com event extraction |
| **EventfulAdapter** | Eventful event extraction |
| **Generic Parser** | Fallback JSON-LD + DOM heuristics |
| **Playwright Engine** | JavaScript rendering for dynamic content |
| **Response Generator** | Consistent event data formatting |

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

## MCP Tools

The Ultimate Event Scraper exposes **6 powerful tools** to Claude and MCP clients:

### 1. scrapeEventPage

Extract comprehensive event details from any event webpage.

**Input:**
```json
{
  "url": "https://www.eventbrite.com/e/conference-2025"
}
```

**Output:**
```json
{
  "event": {
    "source_url": "https://www.eventbrite.com/e/conference-2025",
    "title": "Tech Conference 2025",
    "description": "Annual tech conference for developers and tech enthusiasts...",
    "start": "2025-06-15T09:00:00",
    "end": "2025-06-15T17:00:00",
    "location": "San Francisco, CA, USA",
    "raw_location": { "streetAddress": "...", "addressLocality": "San Francisco" },
    "price": "199",
    "currency": "USD",
    "organizer": "Tech Events Inc",
    "status": "EventScheduled",
    "event_attendance_mode": "OfflineEventAttendanceMode",
    "images": ["https://...image1.jpg", "https://...image2.jpg"],
    "raw_jsonld": { "full": "JSON-LD object if available" }
  },
  "scrape_method": "eventbrite_adapter"
}
```

**scrape_method values:**
- `ticketmaster_adapter` - Ticketmaster-specific extraction
- `eventbrite_adapter` - Eventbrite-specific extraction
- `facebook_adapter` - Facebook Events extraction
- `meetup_adapter` - Meetup.com extraction
- `eventful_adapter` - Eventful extraction
- `static` - Generic JSON-LD parser (static HTML)
- `playwright` - JavaScript-rendered content
- `failed` - Extraction failed

---

### 2. captureEventScreenshot

Capture a screenshot of the event page for visual reference.

**Input:**
```json
{
  "url": "https://www.eventbrite.com/e/conference-2025"
}
```

**Output:**
```json
{
  "screenshot": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "width": 1280,
  "height": 800,
  "format": "png"
}
```

---

### 3. extractEventMedia

Extract all images and videos from the event page.

**Input:**
```json
{
  "url": "https://www.eventbrite.com/e/conference-2025"
}
```

**Output:**
```json
{
  "images": [
    "https://cdn.eventbrite.com/image1.jpg",
    "https://cdn.eventbrite.com/image2.jpg"
  ],
  "videos": [
    {
      "type": "youtube",
      "url": "https://www.youtube.com/watch?v=..."
    },
    {
      "type": "embedded",
      "url": "https://player.vimeo.com/..."
    }
  ],
  "media_count": 5
}
```

---

### 4. generateEventPDF

Create a PDF brochure/document of the event page.

**Input:**
```json
{
  "url": "https://www.eventbrite.com/e/conference-2025"
}
```

**Output:**
```json
{
  "pdf": "data:application/pdf;base64,JVBERi0xLjQ...",
  "filename": "event_conference_2025.pdf",
  "size_bytes": 245000
}
```

---

### 5. checkTicketAvailability

Check real-time ticket availability and pricing information.

**Input:**
```json
{
  "url": "https://www.eventbrite.com/e/conference-2025"
}
```

**Output:**
```json
{
  "url": "https://www.eventbrite.com/e/conference-2025",
  "is_sold_out": false,
  "ticket_status": "available",
  "pricing_text": "From $199 - $499",
  "buy_button_found": true,
  "availability_details": "Limited tickets remaining"
}
```

---

### 6. generateEventCalendar

Generate an iCalendar (ICS) file that can be imported into calendar applications.

**Input:**
```json
{
  "event_data": {
    "title": "Tech Conference 2025",
    "description": "Annual tech conference...",
    "start": "2025-06-15T09:00:00",
    "end": "2025-06-15T17:00:00",
    "location": "San Francisco, CA",
    "source_url": "https://www.eventbrite.com/e/conference-2025"
  }
}
```

**Output:**
```json
{
  "ics": "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Ultimate Event Scraper...",
  "filename": "event.ics",
  "import_url": "webcal://..."
}
```

---

## Usage

### As MCP Server (WebSocket)

```bash
python event_scraper_mcp_server.py
# Server runs on ws://localhost:8765
```

Connect via MCP client and use any of the 6 tools above.

### Using with Claude

The Ultimate Event Scraper integrates seamlessly with Claude via MCP. Claude automatically discovers all 6 tools and can use them intelligently:

```python
# Claude can now:
# 1. Search for events via parent event-aggregator API
# 2. Call scrapeEventPage to extract detailed event info
# 3. Call captureEventScreenshot for visual verification
# 4. Call extractEventMedia to get promotional images
# 5. Call checkTicketAvailability for real-time pricing
# 6. Call generateEventCalendar for calendar imports
```

### Testing

```bash
# Start the server
python event_scraper_mcp_server.py

# In another terminal, test with curl/MCP client
# Or use the parent event-aggregator API gateway
```

### Integration with MCP Security

To integrate with the main MCP Security project:

1. Update `security-mcp/security_gateway/config/servers.yaml`:
```yaml
servers:
  ultimate_scraper:
    command: python
    args: [path/to/event_scraper_mcp_server.py]
    description: "Comprehensive event data extraction and analysis"
```

2. Or use HTTP gateway at: `http://localhost:8765/mcp`

3. Tools are automatically discovered by ConfigManager

No Python code changes needed in the security gateway!

## How It Works

### 1. Request Reception

When a URL is provided to any of the 6 tools:
- **scrapeEventPage** → Main extraction tool
- **captureEventScreenshot** → Screenshot capture
- **extractEventMedia** → Media asset extraction
- **generateEventPDF** → PDF generation
- **checkTicketAvailability** → Ticket status check
- **generateEventCalendar** → ICS calendar generation

### 2. Site Detection & Adapter Selection

The system identifies the event platform:
```
ticketmaster.com        → TicketmasterAdapter
eventbrite.com          → EventbriteAdapter
facebook.com/events     → FacebookEventsAdapter
meetup.com              → MeetupAdapter
eventful.com            → EventfulAdapter
any other site          → Generic Parser
```

### 3. Content Fetching

For each tool:
- **Static HTML** (httpx, 15s timeout) - Fast initial fetch
- **JSON-LD Parser** - Extracts schema.org structured data (most reliable)
- **DOM Heuristics** - Fallback pattern matching
- **Playwright** (30s timeout) - JavaScript rendering for dynamic content (if needed)

### 4. Data Extraction

**Extraction Priority:**
1. Schema.org JSON-LD Event markup (structured data)
2. Site-specific adapters (Ticketmaster patterns, Eventbrite selectors, etc.)
3. OpenGraph meta tags (og:title, og:description, etc.)
4. DOM heuristics (common CSS classes, HTML patterns)
5. Playwright JavaScript rendering (last resort)

### 5. Quality Validation

Events are validated to ensure meaningful data:
```
Requirements: At least 2 of:
  ✓ Title
  ✓ Start date/time
  ✓ Location
```

If validation fails, Playwright is used to re-fetch with full JS execution.

### 6. Tool-Specific Processing

**scrapeEventPage** → Returns event JSON object with all metadata

**captureEventScreenshot** → Playwright renders page, captures PNG

**extractEventMedia** → Finds all img tags, video embeds, YouTube links

**generateEventPDF** → Playwright renders page to PDF

**checkTicketAvailability** → Playwright executes JS, searches for ticket buttons/pricing

**generateEventCalendar** → Formats event data as RFC 5545 iCalendar format

## Adding New Site Adapters

To support a new event platform, extend the `SiteAdapter` abstract class:

### Step 1: Implement Your Adapter

```python
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup

class MyPlatformAdapter(SiteAdapter):
    """Adapter for MyPlatform.com event extraction."""

    def matches(self, url: str) -> bool:
        """Return True if this URL should use this adapter."""
        return "myplatform.com" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract event data from HTML."""
        soup = BeautifulSoup(html, "lxml")

        # Try JSON-LD first (most reliable)
        event_data = _parse_event_from_jsonld(html, url)
        if event_data:
            return event_data

        # Fall back to platform-specific patterns
        title_elem = soup.find("h1", class_="event-title")
        if not title_elem:
            return None  # Let generic parser handle it

        title = title_elem.get_text(strip=True)

        return {
            "source_url": url,
            "title": title,
            "description": self._extract_description(soup),
            "start": self._extract_start_date(soup),
            "end": self._extract_end_date(soup),
            "location": self._extract_location(soup),
            "price": self._extract_price(soup),
            "images": self._extract_images(soup),
            "scrape_method": "myplatform_adapter"
        }

    def _extract_description(self, soup) -> Optional[str]:
        """Platform-specific description extraction."""
        desc = soup.find("div", class_="event-description")
        return desc.get_text(strip=True) if desc else None

    # ... implement other helper methods ...
```

### Step 2: Register in Server

Edit `event_scraper_mcp_server.py` and add to the adapters list:

```python
from ultimate_event_scraper.my_platform_adapter import MyPlatformAdapter

SITE_ADAPTERS = [
    TicketmasterAdapter(),
    EventbriteAdapter(),
    FacebookEventsAdapter(),
    MeetupAdapter(),
    EventfulAdapter(),
    MyPlatformAdapter(),  # ← Add your adapter here
]
```

### Step 3: Test

```bash
# The server will now auto-detect MyPlatform URLs
# and use your custom adapter

python -c "
from event_scraper_mcp_server import get_site_adapter
adapter = get_site_adapter('https://www.myplatform.com/event/123')
print(type(adapter).__name__)  # Should print: MyPlatformAdapter
"
```

## Performance & Optimization

### Response Times

| Scenario | Time | Method |
|----------|------|--------|
| Static site with JSON-LD | ~2-5s | httpx + JSON-LD parser |
| Eventbrite/Ticketmaster | ~3-7s | Adapter + structured data |
| Facebook Events | ~2-4s | OG meta tags |
| JS-heavy site | ~25-35s | Playwright rendering |

### Cold Start Optimization

Playwright is **lazy-loaded** - only imported when needed for JavaScript rendering:

```python
# Fast startup (~1s)
# Playwright only loaded on first dynamic fetch (~30s first time)
# Subsequent calls use cached browser instance
```

### Timeout Strategy

- **HTTP Request:** 15 seconds (configurable via `SCRAPER_REQUEST_TIMEOUT`)
- **Playwright Page Load:** 30 seconds
- **Total Worst Case:** ~45 seconds

### Resource Usage

- **Memory:** ~50-100MB baseline, +200MB when Playwright active
- **CPU:** Minimal for static parsing, intensive during Playwright rendering
- **Network:** ~0.5-2MB per page fetch

### Site-Specific Optimizations

| Site | Strategy | Avg Time |
|------|----------|----------|
| **Ticketmaster** | JSON-LD first | ~4s |
| **Eventbrite** | Adapter + structured data | ~5s |
| **Facebook** | OG meta tags (no JS) | ~3s |
| **Meetup** | JSON-LD + DOM | ~6s |
| **Eventful** | JSON-LD fallback | ~5s |
| **Generic** | Progressive enhancement | ~3-35s |

## Deployment

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# (Optional) Install Playwright for JS rendering
pip install playwright
python -m playwright install chromium

# Start the server
python event_scraper_mcp_server.py
# Server listens on ws://localhost:8765
```

### Docker Deployment

```bash
# Build image
docker build -t ultimate-event-scraper .

# Run container
docker run \
  -p 8765:8765 \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8765 \
  ultimate-event-scraper

# Access via ws://localhost:8765
```

### Modal.com Serverless Deployment

Modal provides a fully managed, serverless runtime ideal for event scraping:

```bash
# Install Modal CLI
pip install modal

# Authenticate
modal token new

# Deploy
modal deploy modal_app.py

# View deployment
modal app list

# Get URL
# https://ultimate-scraper-<hash>.modal.run/mcp
```

**Advantages:**
- Auto-scaling based on demand
- Pre-installed Playwright + Chromium
- No cold start issues for Playwright
- HTTP endpoint included
- Pay-per-use pricing

### Integration with Event-Aggregator API Gateway

The parent project (`event-aggregator/api-gateway/`) has a FastAPI gateway that orchestrates multiple event search services:

```bash
# Start all services
cd event-aggregator

# Terminal 1: Event Scraper
cd mcp-servers/ultimate_event_scraper
python event_scraper_mcp_server.py

# Terminal 2: API Gateway
cd api-gateway
python main.py
# Gateway runs on http://localhost:8000

# Terminal 3: Frontend (optional)
cd ui
npm install && npm run dev
# UI runs on http://localhost:5173
```

The gateway automatically discovers and uses the Ultimate Event Scraper's tools.

## Troubleshooting

### "Failed to extract event" / Empty response

**Diagnosis:**
```python
# The response will show which scrape_method was used
{
  "event": { ... },
  "scrape_method": "failed"  # ← Indicates extraction failed
}
```

**Solutions:**
1. **Check site is supported** - Verify URL matches a known adapter
2. **Verify structure** - Check if site has JSON-LD markup:
   ```bash
   curl https://example.com/event | grep 'application/ld+json'
   ```
3. **Try Playwright** - If static parsing fails, Playwright should auto-attempt
4. **Check timeout** - Site may be slow to load
5. **Add custom adapter** - Create site-specific adapter for structured extraction

### Slow Performance

**Issue:** Response taking >30 seconds

**Causes & Solutions:**
1. **Playwright fallback** - Site likely requires JavaScript
   - Solution: Consider caching or pre-computing results
2. **Network latency** - Site is geographically distant
   - Solution: Use CDN or deploy closer to target
3. **Site rate limiting** - Site blocking requests
   - Solution: Increase timeout, use proxy, or add delays
4. **Undersized hardware** - Running on weak CPU/memory
   - Solution: Increase `SCRAPER_REQUEST_TIMEOUT` or run on faster hardware

**Debug:**
```bash
# Check which method is used
curl -X POST http://localhost:8765/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "scrapeEventPage", "url": "..."}'
```

### Playwright Installation Issues

```bash
# Fresh install
pip install --upgrade playwright
python -m playwright install --with-deps chromium

# If binary is corrupted
rm -rf ~/.cache/ms-playwright/
python -m playwright install chromium

# Check installation
python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

### Memory Issues

**Symptom:** "Out of memory" or process crashes

**Solutions:**
1. **Reduce concurrent requests** - Process one request at a time
2. **Disable Playwright** - Set `USE_PLAYWRIGHT=false` if not needed
3. **Increase system RAM** - Playwright needs ~200MB when active
4. **Run on Modal** - Serverless platform handles scaling

### WebSocket Connection Issues

**Symptom:** "Connection refused" or "timeout"

**Check:**
```bash
# Verify server is running
ps aux | grep event_scraper_mcp_server.py

# Check port is listening
lsof -i :8765  # macOS/Linux
netstat -ano | findstr :8765  # Windows

# Verify from Python
python -c "
import json
from anthropic import Anthropic

client = Anthropic()
# MCP server should be discoverable
"
```

## Event Data Structure

Complete event object returned by `scrapeEventPage`:

```json
{
  "event": {
    "source_url": "https://www.eventbrite.com/e/123456",
    "title": "Tech Conference 2025",
    "description": "Annual tech conference with keynotes and workshops...",
    "start": "2025-06-15T09:00:00",
    "end": "2025-06-15T17:00:00",
    "location": "San Francisco, CA, USA",
    "raw_location": {
      "streetAddress": "101 Market St",
      "addressLocality": "San Francisco",
      "addressRegion": "CA",
      "postalCode": "94105",
      "addressCountry": "US"
    },
    "price": "199",
    "currency": "USD",
    "organizer": "Tech Events Inc",
    "status": "EventScheduled",
    "event_attendance_mode": "OfflineEventAttendanceMode",
    "images": [
      "https://cdn.eventbrite.com/image1.jpg",
      "https://cdn.eventbrite.com/image2.jpg"
    ],
    "raw_jsonld": {
      "@context": "https://schema.org",
      "@type": "Event",
      "name": "Tech Conference 2025",
      "description": "...",
      "startDate": "2025-06-15T09:00:00",
      "endDate": "2025-06-15T17:00:00",
      "location": { "@type": "Place", "name": "San Francisco, CA, USA" },
      "organizer": { "@type": "Organization", "name": "Tech Events Inc" },
      "offers": { "@type": "Offer", "price": "199", "priceCurrency": "USD" }
    }
  },
  "scrape_method": "eventbrite_adapter"
}
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastmcp` | MCP framework for tool definition |
| `httpx` | Async HTTP client for fast fetching |
| `beautifulsoup4` | HTML parsing and DOM manipulation |
| `lxml` | Fast XML/HTML processing |
| `playwright` | Browser automation (lazy-loaded, optional) |
| `python-dotenv` | Environment variable management |

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! To add support for a new event platform:

1. **Create adapter** - Extend `SiteAdapter` class
2. **Implement methods** - `matches()` to detect URLs, `extract_event()` for extraction
3. **Register** - Add to `SITE_ADAPTERS` list in `event_scraper_mcp_server.py`
4. **Test** - Add test cases in test file
5. **Document** - Update README with new site
6. **Submit** - Create PR with changes

## Getting Help

- **Issues** - Report bugs in the [event-aggregator repo](https://github.com/anthropics/event-aggregator)
- **Discussions** - Ask questions in project discussions
- **Integration** - See [YAML_CONFIG_SETUP.md](YAML_CONFIG_SETUP.md) for MCP Security integration

## Related Projects

- **[event-aggregator](../)** - Parent project with API gateway and frontend
- **[MCP Security](../../../../security-mcp/)** - Main MCP security framework
- **[MCP Servers](https://github.com/anthropics/mcp-server-examples)** - Official MCP server examples
