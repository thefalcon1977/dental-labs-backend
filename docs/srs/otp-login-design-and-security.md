# OTP Login — Design, Endpoints, Services, and Security

**Document ID:** SRS-AUTH-OTP-DESIGN
**Status:** Accepted
**Last updated:** 2025-02-07
**Audience:** Developers, Security engineers
**Related:** [otp-login-authentication.md](otp-login-authentication.md), `apps/auth/`, Keycloak, Redis, `SECURITY.md`, `.cursor/rules/security.mdc`

---

## 1. Purpose and Scope

This document specifies the **correct OTP login scenario**, API endpoints, service layers, algorithms, Redis cache usage, rate limiting, and security controls for a two-step login flow:

1. **Step 1 — Login:** Validate credentials with Keycloak; do **not** return tokens; store token in Redis and send OTP (mock, then real SMS).
2. **Step 2 — Verify OTP:** Client sends session id + OTP code; server verifies code, then returns the stored tokens.

The cache backend is **Redis**. All design choices are made with a security-engineer perspective: no credentials in cache, constant-time comparison, rate limits, and safe error responses.

---

## 2. Correct Scenario (High-Level)

| Step | Actor | Action | Result |
|------|--------|--------|--------|
| 1 | Client | `POST /auth/login` with `username`, `password` | Server validates with Keycloak. If valid: create session, store Keycloak token in Redis, send OTP (mock/SMS). Response: `{ "session_id", "message", "expires_in" }` — **no JWT**. If invalid: 401. |
| 2 | Server | — | OTP sent (mock or SMS). Token and OTP state stored in Redis under `session_id`. |
| 3 | Client | `POST /auth/login/verify-otp` with `session_id`, `code` | Server loads session from Redis, verifies OTP (constant-time), enforces attempt limit. |
| 4 | Server | — | If OTP valid: delete session from Redis, return `{ access_token, refresh_token, expires_in, token_type }`. If invalid: increment attempts; after max attempts invalidate session, return 401. |
| 5 | Client | Uses `Authorization: Bearer <access_token>` | Normal authentication and authorization in the system. |

**Principles:**

- **No JWT to client until OTP is verified.** Step 1 never returns `access_token` or `refresh_token`.
- **One-time use:** After successful verify-otp, the session is deleted; the same `session_id` cannot be reused.
- **Short-lived state:** Session and OTP data in Redis have a short TTL (e.g. 5–10 minutes).

---

## 3. API Endpoints

### 3.1 POST /auth/login (Step 1)

**Request:**

```json
{
  "username": "string",
  "password": "string"
}
```

**Success (200/201) — OTP required (no token returned):**

```json
{
  "session_id": "opaque-cryptographically-random-string",
  "message": "OTP sent",
  "expires_in": 300
}
```

**Success (200) — OTP not required (backward compatibility):**
If the system is configured to skip OTP for some users or realms, return the same token payload as today:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 300,
  "token_type": "Bearer"
}
```

**Errors:**

- `401` — Invalid credentials (same as today).
- `429` — Rate limit exceeded (auth/login).
- `503` — Keycloak or Redis unavailable.

**Contract rules:**

- When OTP is required, the response **must not** contain `access_token` or `refresh_token`.
- `session_id` is opaque and unguessable (e.g. 128-bit random, base64url).
- `expires_in` is the session TTL in seconds (client may use for UX).

---

### 3.2 POST /auth/login/verify-otp (Step 2)

**Request:**

```json
{
  "session_id": "string",
  "code": "string"
}
```

- `session_id`: Value returned from Step 1.
- `code`: OTP code (e.g. 6 digits) from user (SMS or mock).

**Success (200):**

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 300,
  "token_type": "Bearer"
}
```

**Errors:**

- `401` — Invalid or expired session, or invalid OTP (generic message; do not distinguish for enumeration).
- `403` — Session locked (too many failed OTP attempts).
- `429` — Rate limit exceeded (verify-otp).
- `503` — Redis unavailable.

**Contract rules:**

- On success, the server **must** invalidate (delete) the session so it cannot be reused.
- Error responses must not leak whether the session existed, how many attempts remain, or the correct OTP.

---

### 3.3 POST /auth/login/resend-otp (Resend OTP)

**Request:**

```json
{
  "session_id": "string"
}
```

- `session_id`: Same value returned from Step 1 (login). Used to identify the existing OTP session.

**Success (200):**

```json
{
  "message": "OTP resent",
  "expires_in": 300
}
```

When `DEBUG=true`, the response may include `dev_otp_code` (mock OTP for testing); never expose in production.

**Errors:**

- `401` — Invalid or expired session (same generic message as verify-otp).
- `429` — Resend rate limit exceeded for this session (e.g. max 3 resends per 15 minutes per session).
- `503` — Redis unavailable.

**Contract and security:**

- Resend **updates** the session: new OTP is generated and stored; failed-attempt counter is **reset** so the user has a fresh OTP and full attempt budget.
- Rate limit is **per session** (key e.g. `auth:otp_rate:resend:{session_id}`) to prevent SMS bombing and abuse without blocking other users.
- Do not leak whether the session existed in 401/429 responses.

---

## 4. Service Layers and Responsibilities

Layered design follows the project architecture (routers → services → repository/utils).

| Layer | Module / component | Responsibility |
|-------|--------------------|----------------|
| **Router** | `apps/auth/routers/login.py` | Parse request (LoginRequest, VerifyOtpRequest); call auth service; return response (LoginOtpRequiredResponse or LoginResponse); handle HTTP status; **no** business logic or Redis access. |
| **Service** | `apps/auth/services/auth_service.py` (or dedicated `otp_login_service.py`) | Orchestrate: (1) login: call Keycloak, create session, store token + OTP in Redis, trigger “send OTP”; (2) verify-otp: load session, verify OTP, enforce attempt limit, return token and invalidate session. Uses **OTP session store** and **rate limiter**; does not contain Redis key layout. |
| **Session store** | `apps/auth/utils/otp_session_store.py` (or `services/otp_session_store.py`) | Create session (write to Redis), get session (read), invalidate session (delete), increment failed-attempt counter. Encapsulates **Redis key format**, TTL, and serialization. |
| **OTP sender** | `apps/auth/services/otp_sender.py` (or utils) | Generate OTP (e.g. 6 digits), store hash or plain in session (via session store contract), send via SMS (later) or mock (log only). **Never** log the actual OTP value. |
| **Rate limiter** | Dedicated auth rate limit (middleware or dependency) | Enforce per-IP and optionally per-user limits for `/auth/login` and `/auth/login/verify-otp`. Return 429 when exceeded. |
| **Keycloak client** | `apps/auth/utils/keycloak_client.py` | Existing: `login_with_password(username, password)` returning token dict. No change to contract; used only in Step 1 to validate credentials and obtain token to store. |

**Data flow:**

- **Login:** Router → Auth service → Keycloak client (get token); Auth service → OTP session store (create session, store token + OTP); Auth service → OTP sender (send OTP); Auth service → Router (return session_id, message, expires_in).
- **Verify-OTP:** Router → Auth service → OTP session store (get session, check attempts); Auth service → constant-time OTP check; Auth service → OTP session store (invalidate); Auth service → Router (return tokens).

---

## 5. Algorithms (Step-by-Step)

### 5.1 Algorithm 1 — POST /auth/login (server-side)

1. **Rate limit check:** If auth rate limit exceeded for this client (e.g. per IP), return `429 Too Many Requests`. Optionally check per-username limit for “send OTP” (e.g. max 5 per 15 minutes).
2. **Validate input:** Ensure `username` and `password` are present and valid format (e.g. non-empty). Return `422` if validation fails.
3. **Call Keycloak:** Request token with `username` and `password` (existing `login_with_password`). If Keycloak returns error (invalid credentials, timeout, 5xx):
   - For invalid credentials: return `401 Unauthorized` (generic message).
   - For Keycloak unavailable: return `503 Service Unavailable`.
4. **Generate session id:** Create a cryptographically random, unguessable `session_id` (e.g. `secrets.token_urlsafe(32)`).
5. **Generate OTP:** Generate a short-lived OTP (e.g. 6-digit numeric). Store it in the session payload (see Section 6). For mock: do not send real SMS; log “OTP sent (mock)” without the code. For production: send via SMS and do not log the code.
6. **Write session to Redis:** Store payload (Keycloak `access_token`, `refresh_token`, `expires_in`, OTP value or hash, `attempts = 0`, `created_at`) under key derived from `session_id`. Set TTL (e.g. 300 seconds). Use the OTP session store API (create_session(session_id, payload, ttl)).
7. **Optional — One pending session per user:** If policy is “one pending OTP per user”, before step 6 delete any existing session key for this user (e.g. secondary index or key pattern). See Section 6.
8. **Response:** Return `200` or `201` with `{ "session_id", "message": "OTP sent", "expires_in": <ttl> }`. Do **not** return any token.

**Backward compatibility:** If configuration says “OTP disabled” for this realm/user, skip steps 4–7 and return the token from step 3 (current behavior).

---

### 5.2 Algorithm 2 — POST /auth/login/verify-otp (server-side)

1. **Rate limit check:** If verify-otp rate limit exceeded (e.g. per IP or per session_id), return `429`.
2. **Validate input:** Ensure `session_id` and `code` are present and valid format. Return `422` if not.
3. **Load session:** Call OTP session store `get_session(session_id)`. If missing or expired:
   - Return `401 Unauthorized` with a generic message (e.g. “Invalid or expired session”). Do **not** distinguish “not found” vs “expired” to avoid enumeration.
4. **Check attempt limit:** If `attempts >= max_attempts` (e.g. 5):
   - Invalidate session (delete from Redis).
   - Return `403 Forbidden` (e.g. “Session locked. Please log in again.”).
5. **Verify OTP:** Compare `code` with stored OTP using **constant-time** comparison (e.g. `secrets.compare_digest(provided_code.strip(), stored_code)`). Normalize format (e.g. strip spaces, same length) before compare.
6. **If OTP invalid:**
   - Increment `attempts` in Redis (atomic increment).
   - If new `attempts >= max_attempts`: invalidate session, return `403` (session locked).
   - Else: return `401` (invalid OTP; generic message).
7. **If OTP valid:**
   - Invalidate session (delete from Redis) so it cannot be reused.
   - Return `200` with `{ "access_token", "refresh_token", "expires_in", "token_type" }` from the stored session payload.
   - Do not log tokens or OTP.

---

## 6. Redis Cache — Key Layout and Storage (Per User and Per Request)

Redis is the **single source of truth** for OTP-pending session state. Design follows: one key per **request** (per login attempt), optionally linked to **user** for “one pending session per user” and rate limiting.

### 6.1 Key Format

| Key pattern | Purpose | Example |
|-------------|---------|--------|
| `auth:otp_session:{session_id}` | OTP-pending session (token + OTP + metadata). One key per login attempt. | `auth:otp_session:a1b2c3d4e5...` |
| `auth:otp_user_pending:{user_id}` | Optional: store `session_id` for a user to enforce “one pending session per user” (value = session_id, TTL = same as session). | `auth:otp_user_pending:keycloak-sub-uuid` |
| `auth:otp_rate:login:{ip}` | Rate limit: login attempts per IP (e.g. 10/min). Increment with INCR, EXPIRE. | `auth:otp_rate:login:192.168.1.1` |
| `auth:otp_rate:verify:{ip}` | Rate limit: verify-otp attempts per IP (e.g. 20/min). | `auth:otp_rate:verify:192.168.1.1` |
| `auth:otp_rate:user:{user_id}` | Optional: “send OTP” per user (e.g. 5 per 15 min). | `auth:otp_rate:user:{user_id}` |

**Recommendation:** Use `session_id` as the primary key. Per-user key is optional and used only when enforcing “one pending session per user” or per-user OTP send rate.

### 6.2 Value Stored Under `auth:otp_session:{session_id}`

Store a **token** and OTP-related data only. **Do not store plaintext password.**

Suggested payload (e.g. JSON):

```json
{
  "access_token": "<from Keycloak>",
  "refresh_token": "<from Keycloak>",
  "expires_in": 300,
  "token_type": "Bearer",
  "otp_code": "<6-digit or hashed; see security note>",
  "attempts": 0,
  "created_at": "<ISO timestamp or epoch>",
  "user_id": "<Keycloak sub, optional for logging/audit>"
}
```

- **Security:** Prefer storing a **hash** of the OTP (e.g. SHA-256) and compare `hash(provided_code) == stored_hash` in constant time. If you store plain OTP for simplicity in mock, ensure Redis is restricted (network, password, TLS in production) and TTL is short.
- **TTL:** Set once at write (e.g. 300 seconds). Use `SET key value EX 300` or `EXPIRE key 300`.
- **Atomicity:** Use Lua or MULTI/EXEC for “get + increment attempts + conditional delete” to avoid races.

### 6.3 When to Write / Read / Delete

| Operation | When | Key(s) |
|-----------|------|--------|
| **Write** | After successful Keycloak login and OTP generation (Step 1). | `auth:otp_session:{session_id}`; optionally `auth:otp_user_pending:{user_id}`. |
| **Read** | On verify-otp (Step 2). | `auth:otp_session:{session_id}`. |
| **Delete** | After successful OTP verification; after max failed attempts; when creating a new session for same user (if one-per-user). | `auth:otp_session:{session_id}`; clear `auth:otp_user_pending:{user_id}` when invalidating. |
| **Increment** | On each failed OTP attempt. | In-place update of `attempts` in same key, or separate key (e.g. `auth:otp_attempts:{session_id}`) with same TTL. |

### 6.4 Fallback When Redis Is Unavailable

- **Step 1 (login):** If Redis is down, do not create a session; return `503 Service Unavailable` with a message that auth is temporarily unavailable. Do not fall back to returning the token without OTP unless explicitly configured (e.g. feature flag “skip OTP when cache down” — not recommended for security).
- **Step 2 (verify-otp):** If Redis is down, return `503`. Do not issue tokens without validating the session.

---

## 7. Rate Limiting

Apply **stricter** limits to auth endpoints than the global API rate limit.

### 7.1 Limits to Enforce

| Scope | Endpoint | Suggested limit | Window | Purpose |
|-------|----------|-----------------|--------|---------|
| Per IP | `POST /auth/login` | 10 requests | 1 minute | Mitigate brute force and abuse. |
| Per IP | `POST /auth/login/verify-otp` | 20 requests | 1 minute | Mitigate brute force on OTP. |
| Per user (optional) | “Send OTP” (Step 1 success) | 5 requests | 15 minutes | Prevent SMS bombing and abuse. |
| Per session | `POST /auth/login/resend-otp` | 3 requests | 15 minutes (900 s) | Prevent SMS bombing; limit resends per session. |
| Per session | Failed OTP attempts | 5 attempts | Session lifetime | Per Algorithm 2; then lock session. |

### 7.2 Implementation

- Use Redis for counters: e.g. `auth:otp_rate:login:{ip}` with INCR and EXPIRE (sliding or fixed window). Or use a dedicated rate-limiting library (e.g. Redis-based) with the same limits.
- Apply in middleware or in a FastAPI dependency for `/auth/login` and `/auth/login/verify-otp`. Return `429 Too Many Requests` with `Retry-After` header when exceeded.
- Log rate-limit hits (WARNING) with low-cardinality data (endpoint name, IP). Do not log username or session_id in production for 429.

### 7.3 Configuration

Make limits configurable via Dynaconf (e.g. `auth.OTP_RATE_LIMIT_LOGIN_PER_MIN`, `auth.OTP_RATE_LIMIT_VERIFY_PER_MIN`, `auth.OTP_RESEND_MAX_PER_SESSION`, `auth.OTP_RESEND_WINDOW_SECONDS`, `auth.OTP_MAX_ATTEMPTS`, `auth.OTP_SESSION_TTL_SECONDS`).

---

## 8. Security Checklist (Security Engineer Perspective)

### 8.1 Credentials and Tokens

- [ ] **Never log** passwords, OTP codes, or access/refresh tokens. Log only non-sensitive identifiers (e.g. `session_id` hash or first 8 chars for debugging, `user_id`).
- [ ] **Never return** tokens in Step 1 response when OTP is required. Return tokens only in verify-otp success response.
- [ ] **Do not store** plaintext password in Redis. Store only the Keycloak token (and OTP/hash) under the session key.
- [ ] **HTTPS only** in production for all auth endpoints.

### 8.2 OTP and Session

- [ ] **Constant-time comparison** for OTP (e.g. `secrets.compare_digest`). Do not use `==` to avoid timing leaks.
- [ ] **Session id:** Cryptographically random (e.g. `secrets.token_urlsafe(32)`). Transmit only in body or header, not in URL.
- [ ] **One-time use:** Delete session from Redis immediately after successful verify-otp. Do not allow reuse of the same `session_id`.
- [ ] **Short TTL:** Session and OTP expire in 5–10 minutes. Rely on Redis EXPIRE.

### 8.3 Error Responses

- [ ] **Generic messages:** Do not distinguish “invalid session” vs “invalid OTP” in a way that allows user/session enumeration. Use a single 401 message like “Invalid or expired session or code.”
- [ ] **No hints:** Do not return “remaining attempts” in production (optional for UX in controlled environments only).
- [ ] **Standard shape:** Use project error format (`error.message`, `error.type`, `error.details`) and document in OpenAPI.

### 8.4 Rate Limiting and Abuse

- [ ] **Auth endpoints** have dedicated, stricter rate limits (per IP for login/verify; per session for resend-otp).
- [ ] **Resend OTP** is rate-limited per session (e.g. 3 per 15 minutes) to prevent SMS bombing.
- [ ] **Session lock** after max failed OTP attempts; require new login (Step 1) to get a new session.
- [ ] **Log and optionally metric** rate-limit hits for alerting.

### 8.5 Redis and Infrastructure

- [ ] Redis **password** and **TLS** in production; restrict network access.
- [ ] **No credentials** in Redis keys or in logs. Keys use only `session_id` or opaque identifiers.
- [ ] **Graceful degradation:** If Redis is down, return 503 for login/verify-otp; do not issue tokens without session validation.

### 8.6 Observability

- [ ] Log high-level events: “Login attempt”, “OTP sent (mock/sms)”, “OTP verified”, “OTP failed”, “Session locked”, “Rate limit exceeded” — without PII or secrets.
- [ ] Use stable, low-cardinality labels for any metrics (e.g. endpoint name, result: success/failure/rate_limited).

---

## 9. Summary Table — Endpoints, Services, and Algorithms

| Item | Detail |
|------|--------|
| **Step 1 endpoint** | `POST /auth/login` — body: username, password. Returns session_id + message + expires_in (no token when OTP required). |
| **Step 2 endpoint** | `POST /auth/login/verify-otp` — body: session_id, code. Returns access_token, refresh_token, expires_in, token_type on success. |
| **Resend endpoint** | `POST /auth/login/resend-otp` — body: session_id. Returns message + expires_in; rate-limited per session (e.g. 3 per 15 min). |
| **Router** | Validates request; calls auth/OTP service; returns response and status codes. |
| **Service** | Orchestrates Keycloak, OTP session store, OTP sender; enforces attempt limit and resend limit; returns token only after OTP success. |
| **Session store** | Redis: create_session, get_session, invalidate, increment_attempts, update_session_otp (resend). Keys: `auth:otp_session:{session_id}`. |
| **Algorithm 1** | Rate limit → Keycloak → session_id + OTP → write Redis → send OTP → response without token. |
| **Algorithm 2** | Rate limit → get session → check attempts → constant-time OTP check → invalidate → return token or 401/403. |
| **Resend OTP** | Resend rate limit (per session) → get session (401 if missing) → new OTP → update_session_otp (reset attempts) → send OTP → response. |
| **Rate limits** | Per IP: login 10/min, verify 20/min. Per session: resend 3 per 15 min; 5 failed OTP attempts then lock. |
| **Security** | No password in Redis; no token in Step 1; constant-time OTP; generic errors; HTTPS; short TTL; one-time session; resend rate-limited per session. |

---

## 10. References

- Existing auth: `apps/auth/routers/login.py`, `apps/auth/services/auth_service.py`, `apps/auth/utils/keycloak_client.py`
- Redis config: `config/settings/settings.toml` (`[redis]`), `config/settings/validators.py`
- SRS: [otp-login-authentication.md](otp-login-authentication.md)
- Project rules: `.cursor/rules/security.mdc`, `fastapi-error-handling.mdc`, `openapi-swagger.mdc`, `architecture.mdc`
