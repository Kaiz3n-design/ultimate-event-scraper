# CORRECTED: How to Actually Add WebScraper to Security Gateway

## The Real Situation

Your security gateway **currently uses hardcoded DOWNSTREAM_SERVERS in Python** (not ConfigManager yet).

ConfigManager exists as a separate module but isn't being used by the gateway yet.

---

## The Correct Setup (5 Minutes)

### Step 1: Edit `security-mcp/security_gateway/config.py`

Add the Ultimate WebScraper to the hardcoded `DOWNSTREAM_SERVERS` dict:

```python
# In security-mcp/security_gateway/config.py

_default_host = os.getenv("DOWNSTREAM_HOST", "localhost")

# Add these lines:
_scraper_url = os.getenv("ULTIMATE_SCRAPER_URL")
_scraper_host = os.getenv("ULTIMATE_SCRAPER_HOST", _default_host)

DOWNSTREAM_SERVERS: Dict[str, DownstreamServerConfig] = {
    "fetch": DownstreamServerConfig(
        key="fetch",
        display_name="Fetch/Web Scraper MCP",
        url=_fetch_url or f"http://{_fetch_host}:9002/mcp",
        tags=["web", "network"],
    ),

    # ADD THIS:
    "ultimate_scraper": DownstreamServerConfig(
        key="ultimate_scraper",
        display_name="Ultimate WebScraper MCP",
        url=_scraper_url or f"http://{_scraper_host}:8765/mcp",
        tags=["web", "events", "scraping"],
    ),
}
```

### Step 2: (Optional) Set Environment Variables

```bash
# Local development (optional, defaults to localhost:8765)
export ULTIMATE_SCRAPER_URL=http://localhost:8765/mcp

# Production (Modal)
export ULTIMATE_SCRAPER_URL=https://event-scraper-mcp--YOUR-HASH.modal.run
```

### Step 3: Start Services

```bash
# Terminal 1: Security Gateway
cd security-mcp
python server.py

# Terminal 2: WebScraper MCP
cd event-aggregator/mcp-servers/ultimate-webscraper-mcp
python event_scraper_mcp_server.py
```

### Step 4: Test

```bash
# Discover tools
curl -X POST http://localhost:8000/tools/refresh

# Call scraper
curl -X POST http://localhost:8000/tools/secure_call \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "judge-1",
    "server": "ultimate_scraper",
    "tool": "scrapeEventPage",
    "arguments": {"url": "https://www.eventbrite.com/e/test"}
  }'
```

---

## Current Architecture

```
server.py
    ↓
imports DOWNSTREAM_SERVERS from config.py
    ↓
registers servers at startup
    ↓
discovers tools from each server
    ↓
ready for secure_call()
```

---

## Future: ConfigManager

ConfigManager is available in `config_manager.py` for future migration to YAML-based config, but it's not being used yet. When/if you migrate, you can switch to:

```python
from security_gateway.config_manager import get_config_manager

config_manager = get_config_manager()
servers = config_manager.load()  # Loads from servers.yaml
```

But for now, the simple approach is **edit config.py**.

---

## Summary

✅ **Edit config.py** - Add ultimate_scraper to DOWNSTREAM_SERVERS dict
✅ **Set env vars** (optional) - For Modal URL override
✅ **Start both services** - Gateway + WebScraper
✅ **Test** - Call secure_call()

No YAML files needed (yet).
