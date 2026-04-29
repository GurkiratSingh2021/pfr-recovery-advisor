# TSG: PilotFish Identity Service Recovery

**Document Type:** TSG  
**Service:** PilotFish.Identity  
**Last Updated:** 2024-02-15  
**Environment:** Production  

---

## Overview

The Identity Service issues OAuth2/OIDC tokens used by all PilotFish components. It depends on the DataStore for credential storage. Token validation failures cascade to the Control Plane API and Gateway.

---

## Prerequisites Before Recovery

1. **PilotFish.DataStore** is healthy and accessible
2. Token-signing certificate is valid (check expiry)
3. No pending key rotation events in the key vault

---

## Symptoms

| Symptom | Likely Cause |
|---|---|
| `token validation failed` in API logs | Identity pods down or cert expired |
| `ICM:auth_failures` elevated | Identity unavailable or DataStore unreachable |
| `token_issuance_p99 > 1000ms` | DataStore latency or identity pod overload |
| OIDC discovery endpoint returns `503` | All identity pods down |

---

## Recovery Procedure

### Step 1 – Check DataStore Connectivity

```bash
kubectl exec -it -n pilotfish-identity deployment/identity-service -- \
  python3 -c "import pyodbc; print('DB OK')"
```

If DataStore is unreachable, recover DataStore first.

### Step 2 – Check Certificate Validity

```bash
kubectl get secret identity-signing-cert -n pilotfish-identity -o jsonpath='{.data.tls\.crt}' \
  | base64 -d | openssl x509 -noout -dates
```

If certificate is expired, rotate it via Key Vault and update the Kubernetes secret.

### Step 3 – Restart Identity Service Pods

```bash
kubectl rollout restart deployment/identity-service -n pilotfish-identity
kubectl rollout status deployment/identity-service -n pilotfish-identity --timeout=300s
```

### Step 4 – Drain and Refresh Identity Cache

If token cache is stale:

```bash
kubectl exec -it -n pilotfish-identity deployment/identity-service -- \
  curl -X POST http://localhost:8080/admin/cache/flush
```

### Step 5 – Verify OIDC Endpoint

```bash
curl -sf https://identity.pilotfish.internal/.well-known/openid-configuration
```

Expected: returns JSON including `issuer`, `jwks_uri`, `token_endpoint`.

### Step 6 – Validate Token Issuance

```bash
curl -s -X POST https://identity.pilotfish.internal/token \
  -d "grant_type=client_credentials&client_id=test&client_secret=test"
```

Expected: `{"access_token": "...", "token_type": "Bearer", "expires_in": 3600}`

---

## Rollback

```bash
kubectl rollout undo deployment/identity-service -n pilotfish-identity
```

If the signing certificate was rotated and caused the issue, restore the previous secret version from Key Vault.

---

## Common Pitfalls

- **Never restart Identity before DataStore is healthy** — pods will fail to initialize
- Certificate rotations must be coordinated; update all dependent services' trust stores
- Cache flush may cause temporary spike in auth latency (expected, resolves in <2 min)
