# TSG: PilotFish Control Plane API Recovery

**Document Type:** TSG  
**Service:** PilotFish.ControlPlane.API  
**Last Updated:** 2024-03-01  
**Environment:** Production  

---

## Overview

This TSG covers recovery procedures for the PilotFish Control Plane API service. The API is the primary HTTP interface for all DM resource operations. It has hard dependencies on the Identity and Config services and a soft dependency on Messaging.

---

## Prerequisites Before Recovery

Before attempting API recovery, validate the following:

1. **PilotFish.Config** service is healthy (`config_fetch_success_rate > 99%`)
2. **PilotFish.Identity** service is healthy (`token_issuance_p99 < 500ms`)
3. No active storage throttling events on the DataStore

Do **not** restart API pods until Config and Identity are confirmed healthy — premature restart will result in repeated CrashLoopBackOff.

---

## Symptoms

| Symptom | Likely Cause |
|---|---|
| `5xx_rate > 20%` on POST endpoints | Config not loaded or Auth middleware failed |
| `token validation failed` in logs | Identity unavailable or cert expired |
| Pods in `CrashLoopBackOff` | Config service unreachable during init |
| `latency_p99 > 5000ms` | DataStore throttling or Messaging backlog |

---

## Recovery Procedure

### Step 1 – Verify Config Service Health

```bash
kubectl get pods -n pilotfish-config
kubectl logs -n pilotfish-config -l app=config-service --tail=50
```

Expected: All pods `Running`, no `FATAL` log entries.

If config service is degraded, resolve that first (see TSG: Config Service Recovery).

### Step 2 – Verify Identity Service Health

```bash
kubectl get pods -n pilotfish-identity
curl -s https://identity.pilotfish.internal/.well-known/openid-configuration | jq .
```

Expected: OIDC discovery endpoint returns valid JSON with `jwks_uri`.

### Step 3 – Rolling Restart of API Pods

Once dependencies are healthy:

```bash
kubectl rollout restart deployment/controlplane-api -n pilotfish-api
kubectl rollout status deployment/controlplane-api -n pilotfish-api --timeout=300s
```

### Step 4 – Verify Config Hot-Reload

Check that the API loaded its configuration successfully:

```bash
kubectl logs -n pilotfish-api -l app=controlplane-api --tail=100 | grep -E "(config|Config)"
```

Expected log: `Configuration loaded successfully from config service`

### Step 5 – Smoke Test

```bash
curl -s https://api.pilotfish.internal/health
curl -s https://api.pilotfish.internal/readiness
```

Expected: `{"status": "healthy"}` and `{"status": "ready"}` respectively.

### Step 6 – Validate Metrics Recovery

Wait 3–5 minutes and confirm:
- `5xx_rate < 1%`
- `latency_p99 < 500ms`
- `auth_failures` count returns to baseline

---

## Rollback

If rolling restart does not resolve the issue:

```bash
kubectl rollout undo deployment/controlplane-api -n pilotfish-api
```

Then escalate to the on-call DRI lead and open a Sev1 ICM if not already done.

---

## Post-Incident

- Capture the time-to-recover and note which step resolved the issue
- Update this TSG if any procedure was inaccurate
- File a follow-up item if Config or Identity caused cascading failure
