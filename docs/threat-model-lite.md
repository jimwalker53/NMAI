# NMIA Threat Model (Lite)

This document provides a lightweight threat model for NMIA using a STRIDE-based
approach. It identifies trust boundaries, assets, threats, current mitigations,
and recommended improvements.

---

## Trust Boundaries

```
+------------------+          +------------------+          +------------------+
|                  |  HTTPS   |                  |   SQL    |                  |
|   React UI       +--------->+   API Server     +--------->+   PostgreSQL     |
|   (Browser)      |  TB-1    |   (FastAPI)      |  TB-2    |   Database       |
|                  +<---------+                  +<---------+                  |
+------------------+          +--------+---------+          +--------+---------+
                                       ^                             ^
                                       | TB-5                        |
                              +--------+---------+          +--------+---------+
                              |                  |   SQL    |                  |
                              |   Admin / CLI    |  TB-3    |   Worker         |
                              |                  |          |   (APScheduler)  |
                              +------------------+          +------------------+
                                                                     ^
                              +------------------+                   |
                              |                  |  HTTP push        |
                              |  Windows         +--------->(via API)|
                              |  Collector       |  TB-4             |
                              |  (certutil)      |                   |
                              +------------------+
```

| Boundary | From | To | Protocol | Notes |
|----------|------|----|----------|-------|
| TB-1 | React UI (browser) | API Server | HTTPS (HTTP in dev) | User-facing, untrusted client |
| TB-2 | API Server | PostgreSQL | TCP/SQL | Internal, credentials in env vars |
| TB-3 | Worker | PostgreSQL | TCP/SQL | Internal, shares DB credentials with API |
| TB-4 | Windows Collector | API Server | HTTP(S) push | Semi-trusted, network-adjacent |
| TB-5 | Admin / CLI | API Server | HTTPS | Privileged operations |

---

## Assets

| Asset | Location | Sensitivity | Notes |
|-------|----------|-------------|-------|
| AD bind passwords | Connector config in DB (JSON field) | **Critical** | Stored in plaintext in database |
| JWT signing secret | `SECRET_KEY` environment variable | **Critical** | Compromise allows token forgery |
| User password hashes | `users` table | **High** | Bcrypt hashed, but still sensitive |
| Certificate metadata | `findings` and `identities` tables | **High** | Includes subject DNs, SANs, requesters |
| Certificate private keys | Not stored (out of scope) | N/A | NMIA only handles metadata, not private keys |
| Connector configurations | `connectors` table | **High** | Contains target URLs, bind DNs, search bases |
| Audit logs | Application logs / DB | **Medium** | Activity records for compliance |
| User role assignments | `user_roles` table | **Medium** | Controls access to enclaves |

---

## Threats (STRIDE)

### Spoofing

| ID | Threat | Likelihood | Impact | Description |
|----|--------|-----------|--------|-------------|
| S-1 | JWT token theft | Medium | High | Attacker steals a valid JWT (via XSS, network sniffing, log exposure) and impersonates the user |
| S-2 | Collector impersonation | Medium | High | Attacker on the network sends fabricated certificate data to the ingest endpoint, injecting false findings |
| S-3 | Credential stuffing | Medium | Medium | Attacker brute-forces the login endpoint using known credential lists |

### Tampering

| ID | Threat | Likelihood | Impact | Description |
|----|--------|-----------|--------|-------------|
| T-1 | Connector config manipulation | Low | Critical | Attacker with operator access modifies a connector to point to a malicious LDAP server, exfiltrating the bind password |
| T-2 | Finding injection | Medium | High | Attacker pushes fabricated findings via the ingest endpoint, polluting the identity inventory |
| T-3 | Database tampering | Low | Critical | Direct DB access allows modification of roles, identities, or connector configs |

### Repudiation

| ID | Threat | Likelihood | Impact | Description |
|----|--------|-----------|--------|-------------|
| R-1 | Audit log gaps | Medium | Medium | Insufficient logging of admin actions (role changes, connector modifications) makes forensic investigation difficult |
| R-2 | Finding provenance deletion | Low | Medium | If findings are deleted, the provenance chain for identities is broken |

### Information Disclosure

| ID | Threat | Likelihood | Impact | Description |
|----|--------|-----------|--------|-------------|
| I-1 | Connector credentials in DB | High | Critical | AD bind passwords stored as plaintext in the `config` JSON column; DB compromise exposes all connector credentials |
| I-2 | Certificate metadata exposure | Medium | Medium | Certificate subjects, SANs, and requesters reveal internal infrastructure topology |
| I-3 | Error message leakage | Medium | Low | Verbose error messages may expose internal paths, DB schema, or stack traces |
| I-4 | JWT secret in environment | Medium | High | `SECRET_KEY` in docker-compose.yml or .env files may be committed to source control |

### Denial of Service

| ID | Threat | Likelihood | Impact | Description |
|----|--------|-----------|--------|-------------|
| D-1 | Unbounded ingest | Medium | Medium | Attacker floods the ingest endpoint with large payloads, exhausting DB storage or API memory |
| D-2 | Large CSV uploads | Medium | Medium | Oversized CSV files to the ingest endpoint consume server memory during parsing |
| D-3 | Expensive queries | Low | Low | Complex filter combinations on the identities endpoint cause slow DB queries |

### Elevation of Privilege

| ID | Threat | Likelihood | Impact | Description |
|----|--------|-----------|--------|-------------|
| E-1 | RBAC bypass | Low | Critical | Logic errors in RBAC middleware allow non-admin users to perform admin operations |
| E-2 | Cross-enclave access | Low | High | Users access resources in enclaves they are not assigned to, due to missing or incorrect scoping checks |
| E-3 | Self-role-escalation | Low | Critical | User modifies their own role assignments via the API |

---

## Current Mitigations

| Mitigation | Threats Addressed | Implementation |
|-----------|-------------------|----------------|
| JWT authentication | S-1, E-1 | `python-jose` HS256 tokens, 60-minute expiry |
| Bcrypt password hashing | S-3 | `passlib` with bcrypt scheme, cost factor 12 |
| RBAC middleware | E-1, E-2, E-3 | Role checks on every endpoint, enclave scoping on queries |
| Enclave scoping | E-2, I-2 | All DB queries filter by user's accessible enclaves |
| Audit logging | R-1 | Application-level logging of key operations |
| Input validation | T-2, D-1 | Pydantic models validate all request bodies |
| Password masking in responses | I-1 | Sensitive connector config fields masked in API responses |
| Soft delete for users | E-3 | Users are deactivated rather than deleted, preserving audit trail |

---

## Recommended Mitigations (TODO)

These are improvements that should be implemented to strengthen the security posture.

### Critical Priority

| Mitigation | Threats Addressed | Approach |
|-----------|-------------------|----------|
| **Encrypt connector secrets at rest** | I-1 | Use Fernet symmetric encryption for connector config sensitive fields. Key stored in environment variable or HashiCorp Vault. Decrypt only at connector execution time. |
| **TLS everywhere** | S-1, I-2 | Enforce HTTPS for all API traffic. In production, terminate TLS at a reverse proxy (nginx, Caddy). Never run HTTP in production. |
| **API key authentication for collector** | S-2, T-2 | Issue per-collector API keys stored in the DB. Collector must present the key on every ingest request. Rotate keys periodically. |

### High Priority

| Mitigation | Threats Addressed | Approach |
|-----------|-------------------|----------|
| **Rate limiting** | S-3, D-1, D-2 | Implement rate limiting on `/auth/login` (e.g., 5 attempts per minute) and `/ingest` (e.g., 100 requests per minute per connector). Use `slowapi` or a reverse proxy. |
| **Request size limits** | D-1, D-2 | Cap request body size at 10MB. Cap CSV row count at 50,000 per upload. |
| **CSP and security headers** | S-1 | Add Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security headers. |
| **JWT secret rotation** | I-4 | Support multiple signing keys with key ID (`kid`) in JWT header. Rotate secrets without invalidating all sessions. |

### Medium Priority

| Mitigation | Threats Addressed | Approach |
|-----------|-------------------|----------|
| **Structured audit logging** | R-1, R-2 | Write audit events to a dedicated `audit_log` table with actor, action, resource, timestamp. Include all admin operations and data modifications. |
| **Input sanitization** | T-2 | Sanitize ingested data beyond Pydantic validation: strip control characters, validate certificate field formats, reject obviously malformed data. |
| **Query complexity limits** | D-3 | Add query timeouts and pagination limits. Maximum page size of 200 records. |
| **Error message sanitization** | I-3 | In production mode, return generic error messages. Log detailed errors server-side only. |

### Low Priority

| Mitigation | Threats Addressed | Approach |
|-----------|-------------------|----------|
| **SAML/OIDC integration** | S-3 | Delegate authentication to enterprise IdP. Reduces password management burden. |
| **Network segmentation** | T-3, I-1 | Run database on an isolated network. Worker communicates only with DB. Collector communicates only with API. |
| **Immutable findings** | R-2 | Enforce append-only semantics on the findings table via DB triggers or application-level controls. |
