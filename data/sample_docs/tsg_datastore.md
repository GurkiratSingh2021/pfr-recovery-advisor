# TSG: PilotFish Data Store Recovery

**Document Type:** TSG  
**Service:** PilotFish.DataStore  
**Last Updated:** 2024-01-30  
**Environment:** Production  

---

## Overview

The Data Store is the foundational persistence layer. It comprises an Azure SQL elastic pool (relational data) and Azure Blob Storage (artifacts). Nearly all PilotFish services depend on it; DataStore recovery must happen first in any full-stack outage.

---

## Prerequisites Before Recovery

1. Confirm the Azure subscription is active and not throttled
2. Confirm you have the correct region failover runbook open
3. Contact Azure Support if the issue is on the Azure platform side

---

## Symptoms

| Symptom | Likely Cause |
|---|---|
| `SLO:read_latency_p99 = timeout` | SQL throttling or region outage |
| `SLO:write_success_rate < 50%` | SQL DTU exhaustion or blob throttling |
| All dependent services degraded simultaneously | DataStore completely unreachable |
| `ECONNREFUSED` or `timeout` in pod logs | Network policy or SQL firewall change |

---

## Recovery Procedure

### Step 1 – Assess Azure SQL Status

Check the Azure portal or use Azure Monitor:

```bash
az sql server show --name pf-sql-prod-eus2 --resource-group pilotfish-prod-rg
az sql db show --server pf-sql-prod-eus2 --resource-group pilotfish-prod-rg \
  --name pilotfish-control-plane-db --query "status"
```

### Step 2 – Check Storage Account

```bash
az storage account show --name pfprodeus2storage --resource-group pilotfish-prod-rg \
  --query "provisioningState"
```

### Step 3 – Verify Network Connectivity

```bash
kubectl exec -it -n pilotfish-infra deployment/network-probe -- \
  nc -zv pf-sql-prod-eus2.database.windows.net 1433
```

If blocked, check NSG rules and Azure SQL firewall rules.

### Step 4 – Check SQL DTU / CPU Usage

```bash
az monitor metrics list --resource /subscriptions/.../pf-sql-prod-eus2/databases/... \
  --metric "dtu_consumption_percent" --interval PT1M
```

If DTU > 90%, scale up the elastic pool temporarily.

### Step 5 – Restart Dependent Services in Order

Once DataStore is healthy, recover dependent services in this order:
1. `PilotFish.Identity`
2. `PilotFish.Config`
3. `PilotFish.Messaging`
4. `PilotFish.ControlPlane.API`
5. `PilotFish.Gateway`

### Step 6 – Validate DataStore Recovery

```bash
kubectl exec -it -n pilotfish-infra deployment/db-healthcheck -- \
  python3 -c "import pyodbc; conn = pyodbc.connect(dsn='...'); print('OK')"
```

---

## Rollback / Escalation

DataStore has no rollback in the traditional sense. If the SQL instance is corrupted:
1. Initiate geo-failover to secondary read replica
2. Alert DRI lead and open a Sev1 ICM
3. Contact Azure Support with subscription ID and resource ARM ID

---

## Common Pitfalls

- Do not scale down the elastic pool during peak hours
- Geo-failover causes up to 30 seconds of unavailability — only use as last resort
- Storage account soft-delete may delay blob recovery by up to 24 hours
