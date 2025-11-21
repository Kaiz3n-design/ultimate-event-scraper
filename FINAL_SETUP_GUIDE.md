# Final Setup Guide: Ultimate WebScraper MCP + Refactored Gateway

## Status: ConfigManager Migration Complete ✓

Your security gateway now uses **YAML-based server configuration** via ConfigManager!

---

## The Simple Setup (5 Minutes)

### Step 1: Verify servers.yaml

The Ultimate WebScraper is already configured in:

**File:** `security-mcp/security_gateway/config/servers.yaml`

```yaml
ultimate_scraper:
  display_name: "Ultimate WebScraper MCP"
  url: "http://localhost:8765/mcp"
  tags: [web, events, scraping]
  enabled: true
  description: "Extract event data from Ticketmaster, Eventbrite, Facebook, Meetup, Eventful..."
```

✅ **No Python code changes needed!** The gateway loads this automatically.

### Step 2: Start Security Gateway

```bash
cd security-mcp
python server.py
```

Gateway will:
- Load servers.yaml via ConfigManager
- Register fetch and ultimate_scraper
- Start discovery process
- Run on http://localhost:8000

### Step 3: Start WebScraper MCP

```bash
cd event-aggregator/mcp-servers/ultimate-webscraper-mcp
python event_scraper_mcp_server.py
```

WebScraper will:
- Start on ws://localhost:8765
- Wait for gateway to discover it

### Step 4: Verify Integration

```bash
# Discover tools (may take a few seconds)
curl -X POST http://localhost:8000/tools/refresh

# List discovered tools
curl http://localhost:8000/tools/list | jq '.tools.ultimate_scraper'

# Should see:
# {
#   "scrapeEventPage": {
#     "name": "scrapeEventPage",
#     "description": "Scrape event details from an event webpage URL"
#   }
# }
```

### Step 5: Test Scraping

```bash
# Call through security gateway
curl -X POST http://localhost:8000/tools/secure_call \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "judge-1",
    "server": "ultimate_scraper",
    "tool": "scrapeEventPage",
    "arguments": {
      "url": "https://www.eventbrite.com/e/test-event-123"
    }
  }'

# Response will include:
# {
#   "allowed": true,
#   "policy_decision": "allow",
#   "risk_score": 0.08,
#   "downstream_result": {
#     "event": {...extracted event data...},
#     "scrape_method": "eventbrite_adapter"
#   }
# }
```

---

## For Production (Modal Deployment)

Just update the URL in `servers.yaml`:

```yaml
ultimate_scraper:
  display_name: "Ultimate WebScraper MCP"
  url: "https://event-scraper-mcp--YOUR-HASH.modal.run"  # Modal URL
  tags: [web, events, scraping]
  enabled: true
```

Or use environment variable:

```bash
export ULTIMATE_SCRAPER_URL=https://event-scraper-mcp--YOUR-HASH.modal.run
python server.py
```

---

## How ConfigManager Works

### Old (Before Refactoring)
```python
# config.py - hardcoded Python dict
DOWNSTREAM_SERVERS = {
    "fetch": DownstreamServerConfig(...),  # had to edit Python!
}
```

### New (After Refactoring)
```yaml
# servers.yaml - YAML configuration
servers:
  fetch:
    display_name: "Fetch/Web Scraper MCP"
    url: "http://localhost:9002/mcp"
    # ...

  ultimate_scraper:
    display_name: "Ultimate WebScraper MCP"
    url: "http://localhost:8765/mcp"
    # ...
```

```python
# config.py - loads from YAML automatically
def get_downstream_servers() -> Dict[str, DownstreamServerConfig]:
    manager = get_config_manager()
    return manager.load()
```

**Benefits:**
✅ Add servers without Python code edits
✅ Clean separation of config and code
✅ Environment variable overrides
✅ Easy for non-developers to configure

---

## Adding More Servers (Super Easy Now!)

Want to add another event scraper or tool? Just edit `servers.yaml`:

```yaml
# Add to servers.yaml
google_calendar:
  display_name: "Google Calendar MCP"
  url: "http://localhost:9003/mcp"
  tags: [calendar, events, google]
  enabled: false  # Can disable without removing

another_scraper:
  display_name: "Custom Event Scraper"
  url: "http://localhost:9004/mcp"
  tags: [web, events, custom]
  enabled: true
```

**Restart the gateway** → New servers automatically discovered!

---

## Configuration Priority

Servers are loaded in this order:

1. **servers.yaml** - Base configuration (edit this file)
2. **Environment variables** - Override any setting
   - `ULTIMATE_SCRAPER_URL=http://custom-host:8765`
   - `ULTIMATE_SCRAPER_ENABLED=false`
3. **servers-discovered.yaml** - Auto-discovered (created automatically)

---

## Troubleshooting

### Tools not discovered?

```bash
# Force refresh
curl -X POST http://localhost:8000/tools/refresh

# Check health
curl http://localhost:8000/health | jq '.downstreams'

# Check WebScraper is running
# Should show: "ultimate_scraper": { "available": true }
```

### Server URL incorrect?

```bash
# Option 1: Edit servers.yaml
nano security-mcp/security_gateway/config/servers.yaml
# Change the url field

# Option 2: Use environment variable
export ULTIMATE_SCRAPER_URL=http://correct-host:8765
python server.py

# Restart gateway
```

### Getting "Unknown server" error?

1. Check server key in servers.yaml matches the request
2. Verify server is enabled: `enabled: true`
3. Call `/tools/refresh` to rediscover
4. Check `ULTIMATE_SCRAPER_ENABLED` env var isn't set to false

---

## Key Files

| File | Purpose |
|------|---------|
| `security-mcp/security_gateway/config/servers.yaml` | ⭐ **SERVER CONFIGURATION** (edit this!) |
| `security-mcp/security_gateway/config.py` | Gateway config + ConfigManager setup |
| `security-mcp/security_gateway/config_manager.py` | ConfigManager implementation |
| `security-mcp/security_gateway/server.py` | Gateway server (loads from servers.yaml) |
| `event-aggregator/mcp-servers/ultimate-webscraper-mcp/` | WebScraper MCP server |

---

## Complete Workflow

```
1. Edit servers.yaml (add/remove/enable-disable servers)
   ↓
2. Start gateway: python server.py
   ↓
3. Gateway loads servers.yaml via ConfigManager
   ↓
4. Gateway discovers downstream tools
   ↓
5. Claude/LLM can call secure_call() for any tool
   ↓
6. Gateway applies security policies and routes to tool
   ↓
7. Tool executes and returns result
   ↓
8. Gateway audits everything
```

---

## What's Different Now?

| Aspect | Before | After |
|--------|--------|-------|
| **Server config** | Hardcoded in config.py | YAML file (servers.yaml) |
| **Adding servers** | Edit Python + restart | Edit YAML + restart |
| **Code changes** | Required | Not required |
| **Backward compat** | N/A | Full (existing code works) |
| **Override** | Limited | Via env vars |
| **Discovery** | Manual | Automatic |

---

## Summary

✅ **ConfigManager migration complete**
✅ **Ultimate WebScraper already configured in servers.yaml**
✅ **No Python code changes needed**
✅ **Backward compatible** (existing code works)
✅ **Production ready** (easy to deploy to Modal)

**You're ready to go!** Just:
1. Start the gateway
2. Start the WebScraper
3. Call secure_call() for scraping

---

## Next: For the Hackathon

1. Test with real Ticketmaster/Eventbrite URLs
2. Verify risk scoring is appropriate
3. Check audit logging works
4. Deploy WebScraper to Modal
5. Update gateway URL in servers.yaml to Modal URL
6. Test full integration with Claude AI

Good luck! 🚀
