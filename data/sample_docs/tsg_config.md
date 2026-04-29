# TSG: PilotFish Config Service Recovery

**Document Type:** TSG  
**Service:** PilotFish.Config  
**Last Updated:** 2024-02-20  
**Environment:** Production  

---

## Overview

The Config Service provides centralized configuration to all PilotFish components. If it is unavailable during API startup, the API pods will crash. It depends on the DataStore for configuration persistence.

---

## Prerequisites Before Recovery

1. **PilotFish.DataStore** is healthy
2. No active schema migration is running
3. Config service bootstrap secret exists in Key Vault

---

## Symptoms

| Symptom | Likely Cause |
|---|---|
| `config_fetch_success_rate < 50%` | Config service pods down or throttled |
| API pods in `CrashLoopBackOff` | Config unreachable during API initialization |
| `ICM:config_propagation_lag > 60s` | Config cache stuck or replication delay |
| Config service pods in `Pending` | Node pressure or PVC mount issue |

---

## Recovery Procedure

### Step 1 – Check DataStore Access

```bash
kubectl exec -it -n pilotfish-config deployment/config-service -- \
  curl -sf http://localhost:8080/admin/db-check
```

If `503`, resolve DataStore first.

### Step 2 – Check Config Schema Migration State

```bash
kubectl exec -it -n pilotfish-config deployment/config-service -- \
  python3 -m alembic current
```

If migration is pending or failed, apply it:

```bash
kubectl exec -it -n pilotfish-config deployment/config-service -- \
  python3 -m alembic upgrade head
```

### Step 3 – Restart Config Service

```bash
kubectl rollout restart deployment/config-service -n pilotfish-config
kubectl rollout status deployment/config-service -n pilotfish-config --timeout=300s
```

To force bootstrap mode (use if normal start fails):

```bash
kubectl set env deployment/config-service -n pilotfish-config BOOTSTRAP=true
kubectl rollout restart deployment/config-service -n pilotfish-config
```

### Step 4 – Force Cache Invalidation

```bash
kubectl exec -it -n pilotfish-config deployment/config-service -- \
  curl -X POST http://localhost:8080/admin/cache/invalidate
```

### Step 5 – Validate Config Service

```bash
curl -s https://config.pilotfish.internal/health
curl -s https://config.pilotfish.internal/api/v1/config/pilotfish-api | jq .version
```

### Step 6 – Monitor Propagation Lag

```bash
kubectl logs -n pilotfish-config -l app=config-service --tail=100 | grep propagation
```

Expected: `Config propagation lag: 0ms` or similar within 30 seconds.

---

## Rollback

```bash
kubectl rollout undo deployment/config-service -n pilotfish-config
kubectl set env deployment/config-service -n pilotfish-config BOOTSTRAP-
```

---

## Common Pitfalls

- Do not restart Config before DataStore — it will enter an infinite restart loop
- Bootstrap flag (`BOOTSTRAP=true`) should only be used during initial recovery, remove it after
- Config propagation lag alarms are normal for up to 60 seconds after restart; wait before escalating
