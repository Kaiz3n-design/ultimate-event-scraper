# Ultimate WebScraper MCP + Security Gateway Integration Checklist

## Overview

This checklist guides you through integrating the Ultimate WebScraper MCP with the Security Gateway's `secure_call()` system.

---

## Pre-Integration Setup

- [ ] **Review Documentation**
  - [ ] Read `SECURITY_GATEWAY_COMPATIBILITY.md` (in this folder)
  - [ ] Understand security gateway architecture
  - [ ] Know your risk tolerance and policies

- [ ] **Verify Prerequisites**
  - [ ] Security Gateway is installed and running
  - [ ] Ultimate WebScraper MCP is in `event-aggregator/mcp-servers/ultimate-webscraper-mcp/`
  - [ ] Python 3.10+ available
  - [ ] Network connectivity between gateway and scraper

- [ ] **Environment Setup**
  - [ ] `.env` file exists with required variables
  - [ ] `DOWNSTREAM_SERVERS` config reviewed
  - [ ] Rate limiting thresholds decided
  - [ ] Risk policy thresholds decided

---

## Phase 1: Configuration

### Step 1.1: Register WebScraper in Gateway (YAML, No Code Changes!)

- [ ] **Edit `security-mcp/security_gateway/config/servers.yaml`**
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
      description: "Extract event details from Ticketmaster, Eventbrite, Facebook, Meetup, Eventful"
      enabled: true
  ```

  > **Note:** Your security gateway uses ConfigManager to load servers dynamically from YAML.
  > See [YAML_CONFIG_SETUP.md](./YAML_CONFIG_SETUP.md) for details.

- [ ] **Update `.env` file**
  ```bash
  # Add WebScraper configuration
  ULTIMATE_SCRAPER_URL=http://localhost:8765/mcp
  # or for Modal:
  ULTIMATE_SCRAPER_URL=https://event-scraper-mcp--YOUR-HASH.modal.run
  ```

### Step 1.2: Configure Security Policies

- [ ] **Decide Rate Limits**
  - [ ] `RATE_LIMIT_MAX_CALLS` = ? per minute (suggest: 100)
  - [ ] `RATE_LIMIT_WINDOW_SECONDS` = ? (suggest: 60)

- [ ] **Decide Risk Thresholds**
  - [ ] `HIGH_RISK_BLOCK_THRESHOLD` = ? (suggest: 0.75)
  - [ ] `MEDIUM_RISK_REDACT_THRESHOLD` = ? (suggest: 0.40)

- [ ] **Set Audit Configuration**
  - [ ] `AUDIT_LOG_PATH` defined (suggest: `/var/log/security-gateway/audit.log`)
  - [ ] Log rotation configured
  - [ ] Retention policy decided (suggest: 90 days)

- [ ] **Configure Plugins** (if customizing)
  - [ ] Review built-in plugins enabled
  - [ ] Decide on additional security plugins
  - [ ] Load any custom plugins

---

## Phase 2: Starting Services

### Step 2.1: Start Security Gateway

- [ ] **Terminal 1: Security Gateway**
  ```bash
  cd security-mcp
  python server.py
  ```

- [ ] **Verify Gateway Started**
  ```bash
  curl http://localhost:8000/health
  # Should return: {"status": "ok"}
  ```

- [ ] **Check Logs**
  ```bash
  tail -f security-mcp/gateway.log
  # Should see: "Starting Security Gateway on port 8000"
  ```

### Step 2.2: Start WebScraper MCP

- [ ] **Terminal 2: WebScraper MCP**
  ```bash
  cd event-aggregator/mcp-servers/ultimate-webscraper-mcp
  python event_scraper_mcp_server.py
  ```

- [ ] **Verify Scraper Started**
  ```bash
  curl http://localhost:8765/health 2>/dev/null || echo "WebSocket only"
  ```

- [ ] **Both Services Running**
  - [ ] Gateway: http://localhost:8000 ✓
  - [ ] Scraper: ws://localhost:8765 ✓

---

## Phase 3: Tool Discovery

### Step 3.1: Discover Downstream Tools

- [ ] **Trigger Tool Discovery**
  ```bash
  curl -X POST http://localhost:8000/tools/refresh
  # Should return list of discovered tools
  ```

- [ ] **Verify WebScraper Tools Discovered**
  ```bash
  curl http://localhost:8000/tools/list | jq '.tools.ultimate_scraper'
  # Should include:
  # {
  #   "scrapeEventPage": {
  #     "name": "scrapeEventPage",
  #     "description": "Scrape event details from an event webpage URL."
  #   }
  # }
  ```

- [ ] **Check for Errors**
  - [ ] No connection refused errors
  - [ ] No timeout errors
  - [ ] No tool discovery errors

---

## Phase 4: Basic Testing

### Step 4.1: Test via HTTP Endpoint

- [ ] **Test Allowed Request (Public Site)**
  ```bash
  curl -X POST http://localhost:8000/tools/secure_call \
    -H "Content-Type: application/json" \
    -d '{
      "user_id": "test-user-1",
      "server": "ultimate_scraper",
      "tool": "scrapeEventPage",
      "arguments": {"url": "https://www.eventbrite.com/e/test-event"}
    }'
  ```

- [ ] **Expected Response Structure**
  - [ ] `allowed: true` or `false`
  - [ ] `policy_decision: "allow" | "redact" | "block"`
  - [ ] `risk_score: number` (0.0-1.0)
  - [ ] `reason: string`
  - [ ] `downstream_result: object` or null

- [ ] **Test Blocked Request (Internal IP)**
  ```bash
  curl -X POST http://localhost:8000/tools/secure_call \
    -H "Content-Type: application/json" \
    -d '{
      "user_id": "test-user-1",
      "server": "ultimate_scraper",
      "tool": "scrapeEventPage",
      "arguments": {"url": "http://192.168.1.1/event"}
    }'
  ```

- [ ] **Expected: Blocked or Redacted**
  - [ ] `allowed: false` or `policy_decision: "redact"`
  - [ ] `risk_score >= 0.40`
  - [ ] Reason explains why

### Step 4.2: Test with Real Event URLs

- [ ] **Test Ticketmaster Event**
  ```bash
  # Use real Ticketmaster event URL
  curl -X POST http://localhost:8000/tools/secure_call \
    -H "Content-Type: application/json" \
    -d '{
      "user_id": "test-user-1",
      "server": "ultimate_scraper",
      "tool": "scrapeEventPage",
      "arguments": {
        "url": "https://www.ticketmaster.com/[REAL-EVENT-ID]"
      }
    }'
  ```

- [ ] **Test Eventbrite Event**
  ```bash
  # Use real Eventbrite event URL
  curl -X POST http://localhost:8000/tools/secure_call \
    -H "Content-Type: application/json" \
    -d '{
      "user_id": "test-user-1",
      "server": "ultimate_scraper",
      "tool": "scrapeEventPage",
      "arguments": {
        "url": "https://www.eventbrite.com/e/[REAL-EVENT-ID]"
      }
    }'
  ```

- [ ] **Test Facebook Event**
  ```bash
  # Use real Facebook event URL
  curl -X POST http://localhost:8000/tools/secure_call \
    -H "Content-Type: application/json" \
    -d '{
      "user_id": "test-user-1",
      "server": "ultimate_scraper",
      "tool": "scrapeEventPage",
      "arguments": {
        "url": "https://www.facebook.com/events/[EVENT-ID]"
      }
    }'
  ```

- [ ] **Verify Results**
  - [ ] Events successfully extracted
  - [ ] Risk scores appropriate (< 0.3 for public sites)
  - [ ] Data quality acceptable

---

## Phase 5: Rate Limiting Verification

- [ ] **Test Rate Limits**
  ```bash
  # Make multiple requests in succession
  for i in {1..5}; do
    curl -X POST http://localhost:8000/tools/secure_call \
      -H "Content-Type: application/json" \
      -d '{"user_id": "test-user-2", "server": "ultimate_scraper", ...}'
  done
  ```

- [ ] **Verify Rate Limit Headers**
  ```bash
  curl -i -X POST http://localhost:8000/tools/secure_call ... | grep -i ratelimit
  # Should show:
  # X-RateLimit-Limit: 100
  # X-RateLimit-Remaining: 95
  # X-RateLimit-Reset: ...
  ```

- [ ] **Test Rate Limit Exceeded**
  - [ ] Make requests > limit
  - [ ] Should get 429 Too Many Requests
  - [ ] Should include `Retry-After` header

---

## Phase 6: Audit Logging Verification

- [ ] **Check Audit Log**
  ```bash
  tail -20 /var/log/security-gateway/audit.log
  # or wherever configured
  ```

- [ ] **Verify Log Entries**
  - [ ] Every call recorded
  - [ ] Timestamps correct
  - [ ] User IDs captured
  - [ ] Tool names correct
  - [ ] Risk scores present
  - [ ] Policy decisions present
  - [ ] Arguments logged (sanitized)

- [ ] **Verify Log Format (JSONL)**
  ```bash
  cat /var/log/security-gateway/audit.log | jq '.user_id, .tool, .policy.allow'
  ```

---

## Phase 7: Production Configuration

### Step 7.1: Deploy WebScraper to Modal

- [ ] **Prepare for Modal**
  - [ ] Review `modal_app.py`
  - [ ] Check `.env` has correct settings
  - [ ] Ensure `requirements.txt` is complete

- [ ] **Deploy WebScraper**
  ```bash
  cd event-aggregator/mcp-servers/ultimate-webscraper-mcp
  modal deploy modal_app.py
  ```

- [ ] **Get Modal URL**
  - [ ] Copy WebSocket URL from Modal output
  - [ ] Format: `wss://event-scraper-mcp--HASH.modal.run`

- [ ] **Update Gateway Config**
  ```bash
  # Edit .env
  ULTIMATE_SCRAPER_URL=wss://event-scraper-mcp--HASH.modal.run
  ```

### Step 7.2: Deploy Security Gateway

- [ ] **Prepare Deployment**
  - [ ] Review all config in `config.py`
  - [ ] Audit log path correct
  - [ ] Rate limits appropriate
  - [ ] Risk thresholds set

- [ ] **Deploy to Production**
  - [ ] Use Docker, systemd, or your platform
  - [ ] Expose on port 8000 (or your choice)
  - [ ] Use HTTPS in production
  - [ ] Set up monitoring/alerting

- [ ] **Verify Production Setup**
  ```bash
  curl https://your-domain.com/health
  # Should return: {"status": "ok"}
  ```

---

## Phase 8: Security Hardening

- [ ] **Enable HTTPS**
  - [ ] SSL certificate obtained
  - [ ] Gateway configured for HTTPS
  - [ ] WebScraper using WSS (secure WebSocket)

- [ ] **Configure Firewall**
  - [ ] Gateway accessible only from Claude/LLM clients
  - [ ] WebScraper accessible only from Gateway
  - [ ] External scraping targets accessible from WebScraper

- [ ] **Set Up Monitoring**
  - [ ] Log aggregation (ELK, Datadog, etc.)
  - [ ] Alert on high risk scores
  - [ ] Alert on blocked requests
  - [ ] Alert on rate limit violations
  - [ ] Alert on errors

- [ ] **Configure Audit Log Rotation**
  ```bash
  # Add to logrotate
  /var/log/security-gateway/audit.log {
      daily
      rotate 90
      compress
      delaycompress
      missingok
      notifempty
  }
  ```

- [ ] **Restrict Access**
  - [ ] Gateway credentials/API keys secured
  - [ ] WebScraper behind firewall
  - [ ] Audit logs readable only by admins

---

## Phase 9: Integration with Claude Client

### Step 9.1: Configure Claude Client

- [ ] **Update MCP Configuration**
  ```json
  {
    "mcpServers": {
      "securityGateway": {
        "command": "python",
        "args": ["-m", "mcp.client", "http://localhost:8000"],
        "env": {}
      }
    }
  }
  ```

- [ ] **Or Use SSE Transport**
  ```python
  from mcp.client.sse import SSEClientTransport

  async with SSEClientTransport("http://localhost:8000") as transport:
      # Tools available:
      # - secure_call()
      # - list_available_tools()
      # - refresh_discovery()
  ```

- [ ] **Test Integration**
  - [ ] Claude can see `secure_call()` tool
  - [ ] Claude can call it with proper arguments
  - [ ] Responses include risk scores and audit info

---

## Phase 10: Ongoing Maintenance

- [ ] **Daily Checks**
  - [ ] Services running (Gateway + WebScraper)
  - [ ] No errors in logs
  - [ ] Audit log being written

- [ ] **Weekly Checks**
  - [ ] Review audit log for anomalies
  - [ ] Check high risk score requests
  - [ ] Verify rate limits working
  - [ ] Monitor performance metrics

- [ ] **Monthly Checks**
  - [ ] Review and update risk policies
  - [ ] Check for security plugin updates
  - [ ] Rotate and archive audit logs
  - [ ] Update allowlists/blocklists if needed
  - [ ] Review blocked request patterns

- [ ] **Quarterly Checks**
  - [ ] Security audit of gateway
  - [ ] Performance analysis
  - [ ] Update documentation
  - [ ] Review and adjust thresholds based on usage

---

## Troubleshooting Checklist

### If Tools Not Discovered

- [ ] Gateway running? `curl http://localhost:8000/health`
- [ ] WebScraper running? `curl http://localhost:8765` (might fail, but not refused)
- [ ] Correct URL in config? Check `config.py`
- [ ] Firewall blocking? Check network connectivity
- [ ] Call `refresh_discovery()` after both started?

### If Risk Score Too High

- [ ] URL is legitimate? Double-check URL
- [ ] Public site? Public sites should be < 0.3
- [ ] Check `risk_factors` in response - what's flagged?
- [ ] Adjust thresholds if intentional
- [ ] Add to URL allowlist if legitimate

### If Calls Are Slow

- [ ] WebScraper hitting Playwright? (slow)
- [ ] Network latency? Test connectivity
- [ ] Site slow to respond? Try another site
- [ ] Increase `SCRAPER_REQUEST_TIMEOUT` if needed

### If Audit Log Not Written

- [ ] Path writable? `ls -ld /var/log/security-gateway/`
- [ ] Disk space? `df -h`
- [ ] Permissions? `whoami`
- [ ] Path in config? Check `AUDIT_LOG_PATH`

---

## Sign-Off

Once all phases complete, sign off:

- [ ] **Integration Complete**
  - [ ] All phases 1-10 checked off
  - [ ] Production tests passed
  - [ ] Monitoring configured
  - [ ] Documentation updated
  - [ ] Team trained

- [ ] **Ready for Production**
  - [ ] Security review passed
  - [ ] Performance acceptable
  - [ ] Audit logging working
  - [ ] Failover plan tested

**Integration Date:** _______________

**Signed By:** _______________

---

## Quick Reference

### Key Files

- Gateway Config: `security-mcp/security_gateway/config.py`
- WebScraper Main: `event-aggregator/mcp-servers/ultimate-webscraper-mcp/event_scraper_mcp_server.py`
- Gateway Docs: `SECURITY_GATEWAY_COMPATIBILITY.md`
- WebScraper Docs: `README.md`, `INTEGRATION_GUIDE.md`

### Key Endpoints

- Gateway Health: `GET http://localhost:8000/health`
- List Tools: `GET http://localhost:8000/tools/list`
- Refresh Tools: `POST http://localhost:8000/tools/refresh`
- Secure Call: `POST http://localhost:8000/tools/secure_call`

### Key Logs

- Gateway: `security-mcp/gateway.log`
- Audit: `/var/log/security-gateway/audit.log` (configurable)

### Key Configs

- Gateway Port: 8000 (config.py)
- WebScraper Port: 8765 (environment variable)
- Rate Limit: 100/60s (config.py)
- High Risk Threshold: 0.75 (config.py)
- Medium Risk Threshold: 0.40 (config.py)

---

## Support

For issues, refer to:
- `SECURITY_GATEWAY_COMPATIBILITY.md` - Compatibility details
- `README.md` - WebScraper usage
- `INTEGRATION_GUIDE.md` - Integration patterns
- Gateway documentation - Security details
