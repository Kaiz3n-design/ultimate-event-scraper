# Ultimate WebScraper MCP - Quick Setup (5 Minutes)

## The Simplest Way to Integrate

### Step 1: Edit ONE YAML File (1 minute)

**File:** `security-mcp/security_gateway/config/servers.yaml`

Add this section:
```yaml
servers:
  ultimate_scraper:
    display_name: "Ultimate WebScraper MCP"
    url: "http://localhost:8765/mcp"
    tags: [web, events, scraping]
    description: "Scrape events from Ticketmaster, Eventbrite, Facebook, Meetup, Eventful"
    enabled: true
```

**That's it! No Python changes needed.**

---

### Step 2: Start Services (2 minutes)

**Terminal 1: Security Gateway**
```bash
cd security-mcp
python server.py
```

**Terminal 2: WebScraper MCP**
```bash
cd event-aggregator/mcp-servers/ultimate-webscraper-mcp
python event_scraper_mcp_server.py
```

---

### Step 3: Test (2 minutes)

```bash
# Discover tools
curl -X POST http://localhost:8000/tools/refresh

# Call the scraper through gateway
curl -X POST http://localhost:8000/tools/secure_call \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "judge-1",
    "server": "ultimate_scraper",
    "tool": "scrapeEventPage",
    "arguments": {"url": "https://www.eventbrite.com/e/test-event"}
  }'

# Response will include:
# {
#   "allowed": true,
#   "policy_decision": "allow",
#   "risk_score": 0.08,
#   "downstream_result": { "event": {...} }
# }
```

---

## Done! ✅

Your WebScraper MCP is now:
- ✅ Registered in gateway
- ✅ Protected by security policies
- ✅ Rate limited
- ✅ Audited
- ✅ Discoverable by Claude AI

---

## For Production (Modal)

Just update the URL in `servers.yaml`:

```yaml
ultimate_scraper:
  display_name: "Ultimate WebScraper MCP"
  url: "https://event-scraper-mcp--YOUR-HASH.modal.run"  # Modal URL
```

Or use environment variable:
```bash
export ULTIMATE_SCRAPER_URL=https://event-scraper-mcp--YOUR-HASH.modal.run
```

---

## Why This Works

Your security gateway's **ConfigManager** automatically:
1. Loads `servers.yaml` at startup
2. Discovers downstream servers
3. Registers tools from all servers
4. Applies security policies
5. Logs all calls

No code changes needed!

---

## Need Details?

See full documentation:
- [YAML_CONFIG_SETUP.md](./YAML_CONFIG_SETUP.md) - Complete YAML guide
- [SECURITY_GATEWAY_COMPATIBILITY.md](./SECURITY_GATEWAY_COMPATIBILITY.md) - Security details
- [GATEWAY_INTEGRATION_CHECKLIST.md](./GATEWAY_INTEGRATION_CHECKLIST.md) - Full checklist
