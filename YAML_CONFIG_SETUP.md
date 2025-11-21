# Ultimate WebScraper MCP - YAML Configuration Setup

## Quick Answer: NO Python Changes Needed! ✓

Your security gateway uses **ConfigManager** to load servers dynamically from `servers.yaml`. You can add the WebScraper MCP without any Python code changes.

---

## Step 1: Create/Edit `servers.yaml`

**Location:** `security-mcp/security_gateway/config/servers.yaml`

```yaml
# servers.yaml - Main server configuration

servers:
  # Existing servers...
  fetch:
    display_name: "Fetch/Web Scraper MCP"
    url: "http://localhost:9002/mcp"
    tags:
      - web
      - network
    description: "Fetch HTTP content and render with browser"

  filesystem:
    display_name: "Filesystem MCP"
    url: "http://localhost:9001/mcp"
    tags:
      - filesystem
      - files
    description: "Read/write files safely"

  # ADD THIS: Ultimate WebScraper MCP
  ultimate_scraper:
    display_name: "Ultimate WebScraper MCP"
    url: "http://localhost:8765/mcp"
    tags:
      - web
      - events
      - scraping
    description: "Scrape event details from Ticketmaster, Eventbrite, Facebook, Meetup, and other event sites"
    enabled: true
    metadata:
      adapters:
        - Ticketmaster
        - Eventbrite
        - Facebook Events
        - Meetup
        - Eventful
      generic_fallback: true
```

---

## Step 2: For Production (Modal Deployment)

**Update URL with environment variable:**

```yaml
# servers.yaml
ultimate_scraper:
  display_name: "Ultimate WebScraper MCP"
  url: "https://event-scraper-mcp--YOUR-HASH.modal.run"
  # ... rest of config
```

**Or use environment variable override:**

In `.env`:
```bash
ULTIMATE_SCRAPER_URL=https://event-scraper-mcp--YOUR-HASH.modal.run
```

The ConfigManager automatically applies overrides in format: `{UPPERCASE_KEY}_URL`

---

## Step 3: That's It!

The ConfigManager will:
1. ✅ Load `servers.yaml` at startup
2. ✅ Discover `ultimate_scraper` server
3. ✅ Register `scrapeEventPage` tool automatically
4. ✅ Apply any environment variable overrides
5. ✅ Persist auto-discovered servers to `servers-discovered.yaml`

**No Python code changes needed!**

---

## ConfigManager Features

Your system automatically handles:

### Loading Priority
1. Main config: `servers.yaml`
2. Auto-discovered: `servers-discovered.yaml` (if exists)
3. Environment overrides: `{SERVER}_URL`, `{SERVER}_ENABLED`

### Dynamic Server Management
```python
config_manager = get_config_manager()

# Load all servers
servers = config_manager.load()

# Get specific server
scraper_config = config_manager.get_server("ultimate_scraper")

# Get enabled servers only
enabled = config_manager.get_enabled_servers()

# List all servers
config_manager.list_servers()
```

### Auto-Discovery
```python
# Automatically save a discovered server to servers-discovered.yaml
config_manager.save_discovered_server(
    key="ultimate_scraper",
    display_name="Ultimate WebScraper MCP",
    url="http://localhost:8765/mcp",
    tags=["web", "events", "scraping"],
    description="Multi-site event scraper"
)
```

---

## File Structure

```
security-mcp/
├── security_gateway/
│   ├── config_manager.py           (loads servers.yaml)
│   ├── server.py                   (uses config_manager)
│   └── config/
│       ├── servers.yaml            (main config - YOU EDIT THIS)
│       └── servers-discovered.yaml (auto-discovered - auto-created)
```

---

## Complete YAML Example

```yaml
# security-mcp/security_gateway/config/servers.yaml

metadata:
  version: "1.0"
  description: "MCP Server Configuration"
  last_updated: "2025-11-20"

servers:
  # Filesystem access
  filesystem:
    display_name: "Filesystem MCP"
    url: "http://localhost:9001/mcp"
    enabled: true
    tags:
      - filesystem
      - files
      - security-sensitive
    description: "Read/write files with security policies"

  # Web scraping (existing)
  fetch:
    display_name: "Fetch/Web Scraper MCP"
    url: "http://localhost:9002/mcp"
    enabled: true
    tags:
      - web
      - network
      - http
    description: "Fetch HTTP content with optional browser rendering"

  # Event scraping (NEW)
  ultimate_scraper:
    display_name: "Ultimate WebScraper MCP"
    url: "http://localhost:8765/mcp"
    enabled: true
    tags:
      - web
      - events
      - scraping
      - data-extraction
    description: "Extract event data from Ticketmaster, Eventbrite, Facebook, Meetup, and other event sites"
    metadata:
      supported_platforms:
        - ticketmaster.com
        - eventbrite.com
        - facebook.com/events
        - meetup.com
        - eventful.com
      generic_fallback: true
      features:
        - site_specific_adapters
        - hybrid_fetching
        - json_ld_parsing
        - dom_heuristics
        - playwright_rendering

  # Google Calendar (example)
  google_calendar:
    display_name: "Google Calendar MCP"
    url: "http://localhost:9003/mcp"
    enabled: false
    tags:
      - calendar
      - events
      - google
    description: "Access Google Calendar events"
```

---

## Environment Variable Overrides

For each server, you can override via environment:

```bash
# Override Ultimate Scraper URL (for production)
export ULTIMATE_SCRAPER_URL=https://event-scraper-mcp--abc123.modal.run

# Enable/disable servers
export ULTIMATE_SCRAPER_ENABLED=true
export FILESYSTEM_ENABLED=false

# Works with ConfigManager._apply_env_overrides()
```

---

## Auto-Discovered Servers File

When servers are dynamically discovered, they're saved here:

**servers-discovered.yaml** (auto-created):
```yaml
metadata:
  auto_discovered: true
  last_updated: "2025-11-20T21:00:00"

servers:
  ultimate_scraper:
    key: ultimate_scraper
    display_name: "Ultimate WebScraper MCP"
    url: "http://localhost:8765/mcp"
    enabled: true
    auto_discovered: true
    discovered_at: "2025-11-20T21:00:00"
    tags:
      - web
      - events
      - scraping
```

---

## Gateway Integration Flow

```
Security Gateway starts
    ↓
ConfigManager loads servers.yaml
    ├→ Reads: ultimate_scraper config
    ├→ Creates: DownstreamServerConfig object
    └→ Registers in _servers dict
    ↓
Tool Discovery triggered
    ├→ Finds ultimate_scraper in registry
    ├→ Connects to http://localhost:8765/mcp
    └→ Discovers scrapeEventPage tool
    ↓
Claude/LLM calls secure_call()
    └→ Routes to ultimate_scraper.scrapeEventPage()
```

---

## Testing

### 1. Verify Config Loads

```bash
cd security-mcp
python -c "
from security_gateway.config_manager import get_config_manager
cm = get_config_manager()
servers = cm.load()
for key, config in servers.items():
    print(f'{key}: {config.display_name}')
"
# Should print:
# fetch: Fetch/Web Scraper MCP
# filesystem: Filesystem MCP
# ultimate_scraper: Ultimate WebScraper MCP
```

### 2. Test Tool Discovery

```bash
# Start gateway
python server.py &

# Discover tools
curl -X POST http://localhost:8000/tools/refresh

# List discovered tools
curl http://localhost:8000/tools/list | jq '.tools.ultimate_scraper'
```

### 3. Test Secure Call

```bash
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

## Updated Integration Checklist

- ✅ **NO Python code changes needed**
- [ ] Create `servers.yaml` in `security-mcp/security_gateway/config/`
- [ ] Add `ultimate_scraper` server config to YAML
- [ ] Start Security Gateway: `python server.py`
- [ ] Start WebScraper MCP: `python event_scraper_mcp_server.py`
- [ ] Trigger tool discovery: `curl -X POST http://localhost:8000/tools/refresh`
- [ ] Verify scrapeEventPage discovered
- [ ] Test with sample URLs

---

## Production Deployment

### For Modal Deployment

```yaml
# servers.yaml
ultimate_scraper:
  display_name: "Ultimate WebScraper MCP"
  # Use environment variable for Modal URL
  url: "${ULTIMATE_SCRAPER_URL}"  # or just hardcode the Modal URL
  enabled: true
  tags:
    - web
    - events
    - scraping
```

**In `.env`:**
```bash
ULTIMATE_SCRAPER_URL=https://event-scraper-mcp--YOUR-HASH.modal.run
```

---

## Summary

✅ **Your system design is perfect:**
- No hardcoded Python server list
- Dynamic YAML-based configuration
- Environment variable overrides
- Auto-discovery support
- Clean separation of concerns

✅ **To add WebScraper MCP:**
1. Edit `servers.yaml`
2. Add 10 lines of YAML config
3. Done!

✅ **No Python changes needed**

Your ConfigManager handles everything else automatically!
