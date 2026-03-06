# AIFont — Incident Response Runbook

This runbook provides step-by-step guidance for responding to incidents
on the AIFont platform.  Each section corresponds to a Prometheus alert or a
common operational scenario.

---

## Table of Contents

1. [General Incident Process](#general-incident-process)
2. [AIFont API Down](#aifont-api-down)
3. [High Error Rate](#high-error-rate)
4. [High Latency](#high-latency)
5. [Agent Errors](#agent-errors)
6. [Slow Agent](#slow-agent)
7. [High CPU](#high-cpu)
8. [Low Memory](#low-memory)
9. [Disk Space Low](#disk-space-low)
10. [Accessing Observability Tools](#accessing-observability-tools)

---

## General Incident Process

```
Detect → Triage → Mitigate → Resolve → Post-mortem
```

| Step | Action |
|------|--------|
| **Detect** | Alert fires in PagerDuty / Slack; on-call engineer is paged. |
| **Triage** | Determine severity (P1–P4) using the table below. |
| **Mitigate** | Apply the first available mitigation to stop the bleeding. |
| **Resolve** | Identify and fix root cause; verify resolution with metrics. |
| **Post-mortem** | For P1/P2 incidents, file a post-mortem within 48 hours. |

### Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| P1 — Critical | Service fully unavailable or data loss | 15 minutes |
| P2 — High | Core feature degraded, > 20 % error rate | 30 minutes |
| P3 — Medium | Non-critical feature degraded, > 5 % error rate | 2 hours |
| P4 — Low | Minor issue, informational | Next business day |

---

## AIFont API Down

**Alert:** `AIFontAPIDown`  
**Severity:** Critical (P1)

### Symptoms
- `up{job="aifont-api"} == 0` for > 1 minute
- HTTP requests return connection errors

### Immediate Actions

1. **Verify the service is actually down**
   ```bash
   curl -f http://aifont-api:8000/healthz
   ```

2. **Check container status**
   ```bash
   docker compose ps aifont-api
   docker compose logs --tail=50 aifont-api
   ```

3. **Restart the service**
   ```bash
   docker compose restart aifont-api
   ```

4. **Verify recovery**
   ```bash
   curl http://aifont-api:8000/healthz
   # → {"status":"ok"}
   ```

### If Restart Fails

- Check for OOM kills: `dmesg | grep -i "killed process"`
- Check disk space: `df -h`
- Review recent deployments: `git log --oneline -10`
- Roll back if a recent deployment caused the issue:
  ```bash
  docker compose pull aifont-api  # pull previous tagged image
  docker compose up -d aifont-api
  ```

### Escalation
If the service cannot be restarted within 10 minutes, escalate to the
Platform Lead and open a P1 incident channel in Slack.

---

## High Error Rate

**Alerts:** `AIFontHighErrorRate` (warning, > 5 %), `AIFontCriticalErrorRate` (critical, > 20 %)  
**Severity:** P2–P3

### Symptoms
- 5xx responses visible in Grafana → *HTTP API* panel → *Request Rate by Endpoint*
- Sentry receiving a surge of new issues

### Diagnostic Queries

```promql
# Which endpoints are failing?
sum(rate(aifont_http_requests_total{status_code=~"5.."}[5m])) by (endpoint)

# What errors are in the logs?
{service="aifont-api"} |= "ERROR" | json | level="ERROR"
```

### Steps

1. Open the **AIFont Platform KPIs** Grafana dashboard.
2. Identify which endpoint(s) have elevated 5xx rates.
3. Open Sentry and filter by the relevant endpoint/module.
4. Examine recent log entries in Loki (use the *AIFont Error Logs* panel).
5. Identify root cause:
   - **Database errors** → check DB connectivity, run migrations.
   - **Dependency unavailable** → check downstream services.
   - **Bug introduced by deployment** → roll back.
6. Apply fix or roll back and verify the error rate drops below 1 %.

---

## High Latency

**Alerts:** `AIFontHighLatency` (warning, P99 > 2 s), `AIFontCriticalLatency` (critical, P99 > 10 s)  
**Severity:** P2–P3

### Diagnostic Queries

```promql
# P50 / P95 / P99 by endpoint
histogram_quantile(0.99,
  sum(rate(aifont_http_request_duration_seconds_bucket[5m])) by (le, endpoint)
)
```

### Steps

1. Identify the slow endpoint(s) using the *Request Latency Percentiles* panel.
2. Check whether latency correlates with an increase in agent run duration.
3. Look for database slow queries in the logs:
   ```
   {service="aifont-api"} |~ "slow query|took [0-9]+s"
   ```
4. Check host CPU / memory — a resource-starved host can cause latency across all endpoints.
5. If the latency is caused by agent pipeline runs:
   - Consider adding a request timeout.
   - Move long-running agent tasks to an async queue (Celery).
6. Scale horizontally if the issue is load-related.

---

## Agent Errors

**Alert:** `AIFontAgentErrors`  
**Severity:** P3

### Diagnostic Queries

```promql
# Which agents are failing?
sum(rate(aifont_agent_run_errors_total[5m])) by (agent_name, error_type)
```

### Steps

1. Identify the failing agent and error type from the *Agent Run Rate by Agent* panel.
2. Check Sentry for the corresponding exception.
3. Review logs:
   ```
   {service="aifont-api"} |= "agent_name" | json | level="ERROR"
   ```
4. Common root causes:
   - **LLM API rate limit** → check API key quotas; add back-off retry.
   - **FontForge binding error** → verify fontforge bindings are installed.
   - **Invalid prompt/input** → add input validation upstream.
5. Apply fix and confirm error rate normalises.

---

## Slow Agent

**Alert:** `AIFontAgentSlowRun`  
**Severity:** P3

### Steps

1. Identify the slow agent from the *Agent Run Duration P95* panel.
2. Check LLM API response times — the agent may be waiting on an upstream service.
3. Check host resource utilisation (CPU / memory / disk I/O).
4. Consider adding a per-agent timeout and circuit breaker.

---

## High CPU

**Alert:** `HighCPUUsage` (> 85 % for 10 min)  
**Severity:** P3

### Steps

1. Identify the offending process:
   ```bash
   top -bn1 | head -20
   ```
2. Check whether CPU spike correlates with a traffic surge (see *Request Throughput* panel).
3. If the process is the AIFont API:
   - Reduce concurrency in uvicorn: `--workers N`.
   - Scale horizontally.
4. If the process is a one-off job, wait for it to complete and monitor.
5. If CPU does not recover, restart the service.

---

## Low Memory

**Alert:** `LowMemoryAvailable` (< 10 % free for 5 min)  
**Severity:** P3

### Steps

1. Identify memory consumers:
   ```bash
   ps aux --sort=-%mem | head -10
   ```
2. Check for memory leaks in the AIFont API (growing RSS over time in the *Memory Usage* panel).
3. Restart the service if memory is not released naturally.
4. Add or lower memory limits in Docker Compose to prevent OOM from affecting other services.
5. Long-term: profile the application for memory leaks.

---

## Disk Space Low

**Alert:** `DiskSpaceLow` (< 15 % free for 5 min)  
**Severity:** P3

### Steps

1. Find large directories:
   ```bash
   du -sh /* 2>/dev/null | sort -rh | head -20
   ```
2. Common culprits:
   - **Docker images / volumes**: `docker system prune -f`
   - **Log files**: `find /var/log -name "*.log" -size +100M`
   - **Prometheus data**: reduce `--storage.tsdb.retention.time`
   - **Loki data**: reduce `retention_period` in `loki.yml`
3. Clear the largest items and verify free space recovers.
4. Set up automated log rotation if not already in place.

---

## Accessing Observability Tools

| Tool | URL | Credentials |
|------|-----|-------------|
| Grafana | http://localhost:3000 | `admin` / `$GRAFANA_ADMIN_PASSWORD` |
| Prometheus | http://localhost:9090 | — |
| Alertmanager | http://localhost:9093 | — |
| Loki (API) | http://localhost:3100 | — |
| AIFont API docs | http://localhost:8000/docs | — |
| Sentry | https://sentry.io | Project credentials |

### Useful Log Queries (Loki / Grafana Explore)

```logql
# All errors from the last hour
{service="aifont-api"} | json | level="ERROR"

# Errors from a specific agent
{service="aifont-api"} | json | agent_name="DesignAgent" | level="ERROR"

# Slow requests (latency > 2s in structured logs)
{service="aifont-api"} | json | duration > 2.0
```

### Useful Prometheus Queries

```promql
# Current request rate
sum(rate(aifont_http_requests_total[2m])) by (endpoint)

# P99 latency by endpoint
histogram_quantile(0.99,
  sum(rate(aifont_http_request_duration_seconds_bucket[5m])) by (le, endpoint)
)

# Agent success ratio
sum(rate(aifont_agent_runs_total{status="success"}[5m])) by (agent_name)
  /
sum(rate(aifont_agent_runs_total[5m])) by (agent_name)

# Total font exports today
sum(increase(aifont_font_exports_total[24h])) by (format)
```

---

*Last updated: 2026-03 — AIFont Platform Team*
