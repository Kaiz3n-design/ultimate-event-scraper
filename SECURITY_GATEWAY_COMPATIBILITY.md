# Ultimate WebScraper MCP - Security Gateway Compatibility

## Executive Summary

✅ **FULLY COMPATIBLE** with the Security Gateway's `secure_call()` system.

The Ultimate WebScraper MCP can be seamlessly integrated as a downstream MCP server and called through the security gateway's risk-based access control system.

---

## Architecture Integration

### How It Fits

```
Claude AI / LLM
      │
      ▼
┌─────────────────────────┐
│  Security Gateway       │
│  Port 8000              │
│                         │
│  ┌───────────────────┐  │
│  │  secure_call()    │  │
│  │  Rate limiting    │  │
│  │  Risk scoring     │  │
│  │  Policy decision  │  │
│  │  Sanitization     │  │
│  │  Auditing         │  │
│  └──────────┬────────┘  │
└─────────────┼───────────┘
              │
    ┌─────────┴──────────┬──────────┬──────────┐
    ▼                    ▼          ▼          ▼
[Filesystem]      [Fetch/Web]  [Ultimate-  [Google
 Server           Scraper MCP   Maps]       Calendar]
```

### Integration Steps

**1. Register WebScraper as Downstream Server** (No Python changes!)

Your security gateway uses ConfigManager to load servers from YAML. Just edit `servers.yaml`:

**File:** `security-mcp/security_gateway/config/servers.yaml`

```yaml
servers:
  # ... existing servers ...

  ultimate_scraper:
    display_name: "Ultimate WebScraper MCP"
    url: "http://localhost:8765/mcp"
    tags:
      - web
      - events
      - scraping
    description: "Extract event data from Ticketmaster, Eventbrite, Facebook, Meetup, and other event sites"
    enabled: true
```

**For production (Modal):**
```yaml
ultimate_scraper:
  display_name: "Ultimate WebScraper MCP"
  url: "https://event-scraper-mcp--YOUR-HASH.modal.run"  # Modal URL
  # ... rest of config
```

See **[YAML_CONFIG_SETUP.md](./YAML_CONFIG_SETUP.md)** for complete configuration guide.

**2. Configure Environment Variables** (`.env`)

```bash
# Ultimate WebScraper location
ULTIMATE_SCRAPER_URL=http://localhost:8765/mcp
# Or with host override:
ULTIMATE_SCRAPER_HOST=event-scraper-mcp.modal.run
# Or global fallback:
DOWNSTREAM_HOST=127.0.0.1
```

**3. Start Both Services**

```bash
# Terminal 1: Security Gateway
cd security-mcp
python server.py
# Runs on http://localhost:8000

# Terminal 2: Ultimate WebScraper MCP
cd event-aggregator/mcp-servers/ultimate-webscraper-mcp
python event_scraper_mcp_server.py
# Runs on ws://localhost:8765
```

**4. Discover Tools**

The security gateway will automatically discover the `scrapeEventPage` tool:

```bash
# Call this to refresh discovered tools
curl http://localhost:8000/tools/refresh

# Or via MCP tool: refresh_discovery()
```

---

## Security Risk Assessment

### Tool Characteristics

| Aspect | Risk Level | Reason |
|--------|-----------|--------|
| **Network Access** | MEDIUM | Makes HTTP requests to arbitrary URLs |
| **Data Sensitivity** | LOW | Extracts public event data |
| **State Modification** | NONE | Read-only, no state changes |
| **Resource Intensity** | MEDIUM | Browser automation (Playwright) uses resources |
| **Data Exfiltration** | LOW | Returns event data, no secrets handling |

### Built-in Protections

The security gateway will automatically apply:

1. **Rate Limiting** - Max N calls per user per minute
2. **URL Validation** - Detects SSRF/malicious URLs
3. **Payload Limits** - Prevents excessively large requests
4. **Output Sanitization** - Redacts emails, phone numbers, etc. if found
5. **Audit Logging** - Records all scraping requests
6. **Policy Enforcement** - Can block/redact based on risk score

---

## Risk Scoring for WebScraper

### Expected Risk Scores by Scenario

| Scenario | Risk Score | Policy | Notes |
|----------|-----------|--------|-------|
| Scraping public Eventbrite | 0.10 | ✓ ALLOW | Low risk, external site |
| Scraping Ticketmaster | 0.10 | ✓ ALLOW | Low risk, public data |
| Scraping localhost event | 0.25-0.35 | ✓ ALLOW | Medium, internal but authorized |
| Scraping 192.168.x.x | 0.50-0.70 | ⚠ REDACT | SSRF risk, internal IP |
| Scraping metadata endpoint | 0.80+ | ✗ BLOCK | High risk SSRF (169.254.169.254) |
| Scraping with token in URL | 0.40+ | ⚠ REDACT | Credentials exposed |

### Risk Factors Detected

The gateway will flag:

✅ **Handled Automatically:**
- External URLs (Eventbrite, Ticketmaster, Facebook) → LOW RISK
- Public event sites → LOW RISK
- Network request (normal for scraper) → +0.10 score

⚠️ **Monitored (may trigger redaction):**
- Internal/private IPs (192.168.*, 10.*, etc.) → +0.50
- Localhost URLs → +0.25
- Potential credentials in arguments → +0.30
- Large response sizes → +0.20

❌ **Blocked:**
- Metadata endpoints (169.254.169.254) → SSRF block
- Jailbreak attempts in llm_context → Jailbreak block
- Rate limit exceeded → Rate limit block

---

## Integration Examples

### Example 1: LLM → Gateway → WebScraper

**User Request:**
> "Scrape this Eventbrite page and tell me about the event"

**Flow:**

```python
# 1. Claude/LLM calls secure_call() via gateway
secure_call(SecureCallInput(
    user_id="judge-1",
    server="ultimate_scraper",
    tool="scrapeEventPage",
    arguments={
        "url": "https://www.eventbrite.com/e/tech-conference-2025"
    },
    llm_context="Help me extract event details"
))

# 2. Gateway processes:
# - Rate limit: judge-1 has 59/60 remaining ✓
# - Tool validation: ultimate_scraper + scrapeEventPage ✓
# - Risk score: 0.08 (low, external public site) ✓
# - Policy: ALLOW ✓
# - Sanitize args: No secrets found ✓
# - Execute downstream call

# 3. WebScraper returns:
{
  "event": {
    "title": "Tech Conference 2025",
    "start": "2025-06-15T09:00:00",
    "location": "San Francisco, CA",
    ...
  },
  "scrape_method": "eventbrite_adapter"
}

# 4. Gateway response:
SecureCallOutput(
    allowed=True,
    policy_decision="allow",
    risk_score=0.08,
    reason="Public event site, external URL, no credentials detected",
    execution_time_ms=2345,
    downstream_result={...event data...}
)
```

### Example 2: Blocked Request (SSRF Attempt)

**Malicious Request:**
```python
secure_call(SecureCallInput(
    user_id="attacker",
    server="ultimate_scraper",
    tool="scrapeEventPage",
    arguments={
        "url": "http://169.254.169.254/latest/meta-data/"  # AWS metadata endpoint
    }
))
```

**Gateway Response:**
```python
SecureCallOutput(
    allowed=False,
    policy_decision="blocked",
    risk_score=0.95,
    reason="SSRF attempt detected: metadata endpoint blocked",
    risk_factors=["ssrf_attempt", "malicious_url"],
    error_category=ErrorCategory.SECURITY_POLICY
)
```

### Example 3: Redacted Response (Sensitive Data)

If scraper returns data containing email addresses:

```python
# Original result has: email: "john@example.com"
# Gateway sanitizes before returning:
downstream_result={
    "event": {
        "title": "Conference",
        "contact": "[REDACTED_EMAIL]"  # Sanitized!
    }
}
```

---

## Configuration Recommendations

### For Development (Local Testing)

**`config.py`:**
```python
DOWNSTREAM_SERVERS = {
    "ultimate_scraper": DownstreamServerConfig(
        key="ultimate_scraper",
        display_name="Ultimate WebScraper MCP",
        url="http://localhost:8765/mcp",
        tags=["web", "events", "scraping"],
    ),
}

# Rate limits for dev
RATE_LIMIT_MAX_CALLS = 1000
RATE_LIMIT_WINDOW_SECONDS = 60

# Risk thresholds
HIGH_RISK_BLOCK_THRESHOLD = 0.75
MEDIUM_RISK_REDACT_THRESHOLD = 0.40
```

### For Production (Modal Deployment)

**`config.py`:**
```python
import os

DOWNSTREAM_SERVERS = {
    "ultimate_scraper": DownstreamServerConfig(
        key="ultimate_scraper",
        display_name="Ultimate WebScraper MCP",
        url=os.getenv("ULTIMATE_SCRAPER_URL",
                      "https://event-scraper-mcp--<hash>.modal.run"),
        tags=["web", "events", "scraping"],
    ),
}

# Production rate limits
RATE_LIMIT_MAX_CALLS = 100
RATE_LIMIT_WINDOW_SECONDS = 60

# Conservative risk thresholds
HIGH_RISK_BLOCK_THRESHOLD = 0.70
MEDIUM_RISK_REDACT_THRESHOLD = 0.35
```

**`.env`:**
```bash
# Production Modal URL
ULTIMATE_SCRAPER_URL=https://event-scraper-mcp--abc123xyz.modal.run

# Audit logging
AUDIT_LOG_PATH=/var/log/security-gateway/audit.log

# Rate limiting per user
RATE_LIMIT_MAX_CALLS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

---

## Security Policies for WebScraper

### Suggested Policy Rules

Add these to your policy engine for fine-grained control:

```python
# Event-specific policies
if tool == "scrapeEventPage":
    # Allow public event sites with low score
    if any(domain in url for domain in [
        "ticketmaster.com",
        "eventbrite.com",
        "facebook.com",
        "meetup.com",
        "eventful.com"
    ]):
        return ALLOW  # Always allow for known public sites

    # For unknown sites, be more cautious
    if risk_score < 0.35:
        return ALLOW
    elif risk_score < 0.55:
        return REDACT_OUTPUT  # Sanitize output
    else:
        return BLOCK
```

### URL Allowlist (Optional)

For strict security, maintain URL patterns:

```python
SCRAPER_ALLOWED_DOMAINS = {
    "ticketmaster.com",
    "eventbrite.com",
    "facebook.com",
    "meetup.com",
    "eventful.com",
    # Add others as needed
}

def check_scraper_url(url: str) -> bool:
    for domain in SCRAPER_ALLOWED_DOMAINS:
        if domain in url.lower():
            return True
    return False

# In policy:
if tool == "scrapeEventPage":
    if not check_scraper_url(url):
        raise PolicyError(f"URL {url} not in allowlist")
```

---

## Monitoring & Auditing

### What Gets Logged

Every `scrapeEventPage` call logs:

```json
{
  "timestamp": "2025-11-20T21:00:00Z",
  "user_id": "judge-1",
  "server": "ultimate_scraper",
  "tool": "scrapeEventPage",
  "raw_arguments": {
    "url": "https://www.eventbrite.com/e/conference-2025"
  },
  "sanitized_arguments": {
    "url": "https://www.eventbrite.com/e/conference-2025"
  },
  "policy": {
    "allow": true,
    "redact_output": false,
    "reason": "Public event site, external URL",
    "risk_score": 0.08
  },
  "risk": {
    "total_score": 0.08,
    "factors": ["network_request:0.10"],
    "threat_count": 0
  },
  "outcome": "success",
  "execution_time_ms": 2345,
  "downstream_result": {
    "event": {...}
  }
}
```

### Metrics to Monitor

```python
# In your monitoring/logging system:
import logging

logger = logging.getLogger("security_gateway.webscraper")

# Log execution
logger.info("scraper.call", extra={
    "user": user_id,
    "url": url,
    "risk_score": risk_score,
    "policy": policy_decision,
    "duration_ms": execution_time_ms
})

# Alert on high risk
if risk_score > MEDIUM_RISK_REDACT_THRESHOLD:
    logger.warning("scraper.elevated_risk", extra={
        "user": user_id,
        "risk_score": risk_score,
        "factors": risk_factors
    })

# Alert on blocked attempts
if policy_decision == "blocked":
    logger.error("scraper.blocked", extra={
        "user": user_id,
        "reason": reason,
        "url": url
    })
```

### Dashboard Queries

You can query the audit log for:

```bash
# All scraper calls by user
grep -E '"user_id":"judge-1".*"tool":"scrapeEventPage"' audit.log.jsonl

# High-risk scraper calls
grep -E '"tool":"scrapeEventPage"' audit.log.jsonl | \
  jq 'select(.policy.risk_score > 0.4)'

# Blocked scraper attempts
grep -E '"tool":"scrapeEventPage"' audit.log.jsonl | \
  jq 'select(.policy.allow == false)'

# Performance analysis
grep -E '"tool":"scrapeEventPage"' audit.log.jsonl | \
  jq '.execution_time_ms' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'
```

---

## Step-by-Step Integration Guide

### Step 1: Update Gateway Configuration

```bash
# Edit security-mcp/security_gateway/config.py
nano config.py

# Add this section:
DOWNSTREAM_SERVERS = {
    ...existing servers...,

    "ultimate_scraper": DownstreamServerConfig(
        key="ultimate_scraper",
        display_name="Ultimate WebScraper MCP",
        url=os.getenv(
            "ULTIMATE_SCRAPER_URL",
            "http://localhost:8765/mcp"
        ),
        tags=["web", "events", "scraping"],
    ),
}
```

### Step 2: Start Security Gateway

```bash
cd security-mcp
python server.py
# Should start on http://localhost:8000
```

### Step 3: Start WebScraper MCP

```bash
cd event-aggregator/mcp-servers/ultimate-webscraper-mcp
python event_scraper_mcp_server.py
# Should start on ws://localhost:8765
```

### Step 4: Discover Tools

```bash
# Refresh tool discovery
curl -X POST http://localhost:8000/tools/refresh

# Verify scrapeEventPage is discovered
curl http://localhost:8000/tools/list | jq '.tools.ultimate_scraper'
```

Should return:
```json
{
  "scrapeEventPage": {
    "name": "scrapeEventPage",
    "description": "Scrape event details from an event webpage URL."
  }
}
```

### Step 5: Test via Gateway

```bash
# Call via gateway
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

# Should get response with:
# - allowed: true
# - policy_decision: "allow"
# - downstream_result: { event data }
```

### Step 6: Update Claude Client Configuration

In your Claude client's MCP config, use the gateway:

```json
{
  "mcpServers": {
    "securityGateway": {
      "command": "python",
      "args": ["-m", "fastmcp.client", "http://localhost:8000"],
      "env": {}
    }
  }
}
```

---

## Compatibility Checklist

- ✅ Tool accepts structured input (URL string)
- ✅ Tool returns structured output (JSON with event data)
- ✅ No authentication required between gateway and scraper
- ✅ Runs on separate port (8765) from gateway (8000)
- ✅ Supports MCP HTTP protocol
- ✅ Stateless (no session/context needed)
- ✅ No side effects (read-only operation)
- ✅ Handles errors gracefully
- ✅ Reasonable timeout (30s for Playwright)
- ✅ Can sanitize sensitive data (emails, URLs, etc.)

---

## Troubleshooting

### Issue: Tool not discovered

**Problem:** After calling `/tools/refresh`, `scrapeEventPage` doesn't appear

**Solutions:**
1. Verify WebScraper MCP is running: `curl http://localhost:8765/health`
2. Check URL in config matches actual server address
3. Look at gateway logs: `tail -f /var/log/security-gateway/*.log`
4. Try manual discovery: `curl http://localhost:8000/tools/refresh -v`

### Issue: "Unknown tool" error

**Problem:** `secure_call()` returns "Unknown tool 'scrapeEventPage'"`

**Solutions:**
1. Call `list_available_tools()` first to populate cache
2. Call `/tools/refresh` endpoint
3. Verify tool name is exactly `scrapeEventPage` (case-sensitive)

### Issue: High risk score for legitimate URLs

**Problem:** Event URLs are getting risk score > 0.4, causing redaction

**Solutions:**
1. Add URL patterns to allowlist in policy
2. Adjust risk thresholds in config
3. Check which risk factors are firing: look at `risk_factors` in response
4. Disable specific plugins if over-aggressive

### Issue: Playwright timeout

**Problem:** Calls to JS-heavy sites timeout after 30s

**Solutions:**
1. Increase `SCRAPER_REQUEST_TIMEOUT` in `.env`
2. Test directly: `python event_scraper_mcp_server.py` and call manually
3. Try static-only sites first (Ticketmaster, Eventbrite are good)

---

## Performance Notes

### Latency Expectations

```
Gateway overhead:
  Rate limit check:    ~1ms
  Tool validation:     ~1ms
  Risk scoring:        ~5-10ms
  Policy decision:     ~1ms
  Sanitization:        ~2-3ms
  Audit logging:       ~2-3ms

Total gateway:        ~15-25ms

WebScraper overhead:
  Static HTML:        ~2-3s
  JSON-LD parsing:    ~10-50ms
  DOM parsing:        ~50-100ms
  Playwright:         ~15-20s

Total scraper:       ~2s - 20s (depending on site)

Total end-to-end:    ~2.1s - 20.1s
```

### Optimization Tips

1. **Caching Results** - Same URL called multiple times?
   - Add caching layer in gateway
   - Cache by URL hash for 24 hours

2. **Bulk Operations** - Scraping multiple URLs?
   - Use batch processing with concurrency control
   - Keep concurrent requests under 5-10

3. **Site Optimization** - Some sites consistently slow?
   - Increase `SCRAPER_REQUEST_TIMEOUT` per-site
   - Consider allowlisting only fast sites

---

## Security Best Practices

✅ **DO:**
- Use HTTPS URLs for deployed systems
- Monitor audit logs for suspicious patterns
- Set up alerts for blocked requests
- Use URL allowlists for strict environments
- Regularly review risk scores and adjust thresholds
- Keep security plugins updated
- Rotate audit log files daily

❌ **DON'T:**
- Disable rate limiting
- Lower risk thresholds without reason
- Scrape sites you don't have permission for
- Disable audit logging
- Run gateway and scraper on same machine (resource contention)
- Expose gateway/scraper to untrusted networks

---

## Summary

The Ultimate WebScraper MCP is **fully compatible** with your security gateway's `secure_call()` system:

1. ✅ Tool structure matches expected interface
2. ✅ Risk scoring will handle scraper appropriately
3. ✅ Policy engine can enforce controls
4. ✅ Audit logging captures all details
5. ✅ Easy to register as downstream server
6. ✅ Works with rate limiting
7. ✅ Output can be sanitized as needed

**Next Steps:**
1. Follow "Step-by-Step Integration Guide" above
2. Test with sample URLs
3. Configure policies for your use case
4. Set up monitoring and alerting
5. Deploy to production

Your security gateway provides multiple layers of protection for the scraper, making it safe to deploy in production environments.
