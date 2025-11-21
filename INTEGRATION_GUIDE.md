# Integration Guide: Ultimate WebScraper MCP

This guide explains how to integrate the Ultimate WebScraper MCP into your event aggregator system.

## Quick Integration Steps

### 1. Local Development Setup

```bash
# In ultimate-webscraper-mcp directory
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start the server
python event_scraper_mcp_server.py
# Runs on ws://localhost:8765
```

### 2. Add to Your MCP Manifest

In your Claude client's MCP configuration file, add:

```json
{
  "mcpServers": {
    "eventScraper": {
      "command": "python",
      "args": ["event_scraper_mcp_server.py"],
      "cwd": "path/to/event-aggregator/mcp-servers/ultimate-webscraper-mcp",
      "env": {
        "MCP_HOST": "0.0.0.0",
        "MCP_PORT": "8765"
      }
    }
  }
}
```

### 3. Use in Your Application

#### Python Integration

```python
from event_scraper_mcp_server import hybrid_fetch

# Scrape any event URL
result = hybrid_fetch("https://www.eventbrite.com/e/conference-2025")

event = result["event"]
method = result["scrape_method"]

print(f"Event: {event['title']}")
print(f"Date: {event['start']}")
print(f"Location: {event['location']}")
print(f"Method: {method}")
```

#### HTTP/WebSocket Integration

```python
import asyncio
from mcp.client.sse import SSEClientTransport
from mcp.client.stdio import StdioClientTransport

# For WebSocket (recommended)
async def scrape_event(url: str):
    async with SSEClientTransport("ws://localhost:8765") as transport:
        # Call scrapeEventPage tool
        result = await transport.call_tool(
            "scrapeEventPage",
            {"url": url}
        )
        return result
```

#### REST API Wrapper

```python
from fastapi import FastAPI
from event_scraper_mcp_server import hybrid_fetch

app = FastAPI()

@app.post("/scrape-event")
async def scrape_event_endpoint(url: str):
    result = hybrid_fetch(url)
    return {
        "event": result["event"],
        "scrape_method": result["scrape_method"],
        "success": result["event"] is not None
    }
```

## Integrating with Existing MCP Servers

### Architecture

```
API Gateway
    │
    ├─ Eventbrite MCP (API-based)
    ├─ Ticketmaster MCP (API-based)
    └─ Ultimate Scraper MCP (for fallback/unlisted sites)
```

### Adding to API Gateway

```python
# In api-gateway/main.py
from mcp.client.sse import SSEClientTransport
from event_scraper_mcp_server import hybrid_fetch

class ScraperClient:
    def __init__(self):
        self.local_scraper = hybrid_fetch  # Use local for now

    async def scrape(self, url: str):
        """Fallback scraper for sites not covered by APIs."""
        try:
            result = self.local_scraper(url)
            return result["event"]
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            return None

# In your endpoint
@app.post("/events/scrape")
async def scrape_event(url: str):
    # Try official APIs first
    for api_client in [eventbrite_client, ticketmaster_client]:
        event = await api_client.search_url(url)
        if event:
            return event

    # Fall back to scraper
    event = await scraper.scrape(url)
    if event:
        return event

    return {"error": "Could not extract event"}
```

## Use Cases

### 1. User-Provided URLs

Allow users to paste any event URL:

```python
async def extract_from_user_url(url: str):
    """
    Extract event details from any URL the user provides.
    Works with known sites (optimized) and unknown sites (generic).
    """
    result = hybrid_fetch(url)

    if result["event"] and result["event"]["title"]:
        return {
            "success": True,
            "event": result["event"],
            "confidence": result["scrape_method"]  # Which adapter was used
        }

    return {"success": False, "error": "Could not extract event"}
```

### 2. Event Calendar Aggregation

Combine data from multiple sources:

```python
async def aggregate_events(urls: List[str]):
    """
    Scrape multiple event URLs and aggregate results.
    Deduplicates by normalizing titles and dates.
    """
    events = []

    for url in urls:
        result = hybrid_fetch(url)
        if result["event"]:
            events.append({
                "source_url": url,
                "data": result["event"],
                "extraction_method": result["scrape_method"]
            })

    # Deduplicate similar events
    return deduplicate_events(events)
```

### 3. Event Discovery Bot

Create a bot that finds and indexes events:

```python
async def discover_events(keywords: str, locations: List[str]):
    """
    Find event URLs using search, then scrape for details.
    Works with any event site that has schema.org markup.
    """
    urls = await search_event_urls(keywords, locations)

    events = []
    for url in urls:
        result = hybrid_fetch(url)
        if result["event"]:
            events.append(result["event"])

    return events
```

## Performance Tips

### 1. Caching Results

```python
from functools import lru_cache
import hashlib

# Cache scraping results by URL hash
@lru_cache(maxsize=1000)
def scrape_cached(url: str):
    cache_key = hashlib.md5(url.encode()).hexdigest()

    if cache.has(cache_key):
        return cache.get(cache_key)

    result = hybrid_fetch(url)

    # Cache for 24 hours
    cache.set(cache_key, result, ttl=86400)

    return result
```

### 2. Batch Processing

```python
async def scrape_batch(urls: List[str], max_concurrent=5):
    """Scrape multiple URLs with concurrency control."""
    from asyncio import Semaphore

    semaphore = Semaphore(max_concurrent)

    async def bounded_scrape(url):
        async with semaphore:
            return hybrid_fetch(url)

    tasks = [bounded_scrape(url) for url in urls]
    results = await asyncio.gather(*tasks)

    return results
```

### 3. Progressive Enhancement

```python
def scrape_with_fallback(url: str, max_attempts=2):
    """
    Try scraping multiple times if needed.
    Useful for unreliable networks.
    """
    for attempt in range(max_attempts):
        try:
            result = hybrid_fetch(url)
            if result["event"] and result["event"].get("title"):
                return result
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")

    return {"event": None, "scrape_method": "failed_all_attempts"}
```

## Monitoring & Logging

### Add Logging

```python
import logging

logger = logging.getLogger("scraper")

def hybrid_fetch_with_logging(url: str):
    logger.info(f"Scraping: {url}")

    start_time = time.time()
    result = hybrid_fetch(url)
    duration = time.time() - start_time

    event = result["event"]
    method = result["scrape_method"]

    logger.info(
        f"Scraped {url}",
        extra={
            "duration": duration,
            "method": method,
            "success": event is not None,
            "title": event.get("title") if event else None
        }
    )

    return result
```

### Metrics

Track which adapters are being used:

```python
from prometheus_client import Counter, Histogram

scrape_attempts = Counter(
    "scraper_attempts_total",
    "Total scraping attempts",
    ["adapter", "status"]
)

scrape_duration = Histogram(
    "scraper_duration_seconds",
    "Scraping duration",
    ["adapter"]
)

def scrape_with_metrics(url: str):
    adapter = get_site_adapter(url)
    adapter_name = adapter.__class__.__name__ if adapter else "generic"

    with scrape_duration.labels(adapter=adapter_name).time():
        result = hybrid_fetch(url)

    status = "success" if result["event"] else "failed"
    scrape_attempts.labels(adapter=adapter_name, status=status).inc()

    return result
```

## Troubleshooting Integration

### Issue: WebSocket Connection Refused

```
Error: Failed to connect to ws://localhost:8765
```

**Solution:**

1. Verify server is running: `python event_scraper_mcp_server.py`
2. Check port 8765 is not blocked by firewall
3. Use `0.0.0.0` instead of `localhost` for broader access

### Issue: Slow Scraping

**Solution:**

1. Enable caching for frequently scraped URLs
2. Increase `SCRAPER_REQUEST_TIMEOUT` for slow sites
3. Use batch processing instead of sequential

### Issue: Poor Extraction Quality

**Solution:**

1. Check which `scrape_method` was used
2. If it's generic parser, site might benefit from custom adapter
3. Enable Playwright for JS-heavy sites: `PLAYWRIGHT_ENABLED=true`

## Adding Custom Adapters for Your Data

```python
# Add to event_scraper_mcp_server.py

class YourCustomEventSiteAdapter(SiteAdapter):
    """Adapter for your proprietary event site."""

    def matches(self, url: str) -> bool:
        return "youreventsiteapi.com" in url.lower()

    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        # Custom extraction for your specific site
        soup = BeautifulSoup(html, "lxml")

        # ... your extraction logic ...

        return {
            "source_url": url,
            "title": title,
            # ... other fields ...
            "scrape_method": "your_custom_adapter"
        }

# Register it
SITE_ADAPTERS.append(YourCustomEventSiteAdapter())
```

## Next Steps

1. ✅ **Deploy** to Modal or Docker
2. ✅ **Integrate** with API Gateway
3. ✅ **Add** custom adapters for your sites
4. ✅ **Monitor** scraping metrics
5. ✅ **Cache** results for performance
6. ✅ **Test** with real URLs from all platforms

## Support

- See [README.md](./README.md) for technical details
- Check [requirements.txt](./requirements.txt) for dependencies
- Run [test_scraper_local.py](./test_scraper_local.py) to verify setup
