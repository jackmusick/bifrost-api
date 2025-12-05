# Authentication & OAuth Security Review

**Date:** 2025-12-05  
**Reviewer:** opencode (AI assistant)  
**Context:** Bifrost API JWT/cookie/OAuth implementation; local development stage; React frontend; need secure auth patterns for production readiness.

---

## 1. Overview & Threat Model

- **Trust boundary:** Browser clients (React), service clients (API keys), OAuth providers (Microsoft, Google, OIDC).
- **Current stage:** Local development, no external users.
- **Key assumptions:**
  - Cookies are primary auth mechanism for browsers (automatic `HttpOnly`+`Secure` cookies).
  - Service-to-service uses `Authorization: Bearer`.
  - Multi-tenant isolation via `X-Organization-Id` header (platform-admin convenience).
  - OAuth providers are trusted for authentication (bypass MFA).
- **Threats considered:** CSRF, token reuse/leakage, OAuth state tampering, refresh‑token abuse, account takeover via weak endpoints, insufficient multi‑tenant checks.

---

## 2. Critical Findings (Must Fix Before Production)

### 2.1. Refresh tokens accepted as access tokens
- **Location:** `api/src/core/auth.py:get_current_user_optional`, `get_current_user`, WebSocket auth.
- **Issue:** `decode_token` does not validate token type; a refresh token (type=`"refresh"`) passes authentication and yields a `UserPrincipal`.
- **Impact:** Any valid refresh token can be used as a bearer token for protected API calls → privilege escalation.
- **Root cause:** No explicit `type="access"` check; refresh tokens contain only `sub` and `type` claims.
- **Fix:** Add `type="access"` to access tokens; reject tokens where `type != "access"` in bearer auth.

### 2.2. `/auth/oauth/login` trusts client-supplied email without verification
- **Location:** `api/src/routers/auth.py:oauth_login`.
- **Issue:** Endpoint accepts `{ email, name, provider }` and issues full JWTs with roles and organization assignments. No proof of OAuth completion (no code/verifier/ID token validation).
- **Impact:** Account takeover: attacker can POST any email and receive valid access/refresh tokens for that user.
- **Fix:** Remove endpoint or require a verified OAuth artifact (authorization code + PKCE verifier or validated ID token). Use the existing `/auth/oauth/callback` flow for all OAuth logins.

### 2.3. OAuth state not validated; PKCE verifier handled client‑side
- **Location:** `api/src/routers/oauth_sso.py:oauth_callback`.
- **Issue:** 
  - `state` generated in `/init` but never validated on callback → CSRF/open‑redirect risk.
  - PKCE code verifier is returned to frontend in response; server does not store or bind it to the state.
- **Impact:** Potential OAuth flow tampering; though PKCE is still enforced by provider, missing state validation weakens CSRF protection.
- **Fix:** 
  - Store `state` server‑side (Redis) or use HMAC‑signed state token; validate on callback.
  - Bind PKCE verifier to the state (store or sign it) and re‑derive challenge on callback.

### 2.4. No refresh token rotation or revocation
- **Issue:** Refresh tokens are long‑lived (7 days), symmetric JWTs with no server‑side state. Theft → unlimited refresh until secret rotates.
- **Impact:** Cannot revoke individual sessions or tokens; stolen refresh tokens are permanent.
- **Fix:** 
  - Add `jti` (JWT ID) and `iat` (issued‑at) to refresh tokens.
  - Store `jti` in Redis with TTL; on refresh, verify presence, rotate to new `jti`, delete old.
  - Add admin/user revoke endpoints that delete all JTIs for a user.

### 2.5. Cookie‑based auth without CSRF protection
- **Location:** `api/src/routers/auth.py:set_auth_cookies`.
- **Issue:** Cookies are `HttpOnly`, `Secure`, `SameSite=Lax` (prod only). While `SameSite=Lax` blocks cross‑site POSTs, any state‑changing GET endpoints remain vulnerable.
- **Impact:** CSRF attacks possible if any unsafe GET endpoints exist.
- **Fix:**
  - Add CSRF double‑submit token (set‑cookie + `X-CSRF-Token` header) and enforce for unsafe methods when cookie auth is used.
  - Consider `SameSite=Strict` if UX permits.
  - Ensure no state‑changing GETs.

### 2.6. JWT lacks issuer/audience validation
- **Location:** `api/src/core/security.py:decode_token`.
- **Issue:** Only signature and `exp` are validated; any HS256 token signed with the same secret is accepted regardless of `iss`/`aud`.
- **Impact:** If secret is reused elsewhere, tokens from other systems could be accepted.
- **Fix:** Add `iss` and `aud` claims when issuing; verify in `decode_token`. Use simple values (e.g., `iss=bifrost-api`, `aud=bifrost-client`).

### 2.7. WebSocket auth allows token via query parameter
- **Location:** `api/src/core/auth.py:get_current_user_ws`.
- **Issue:** Query parameter `?token=...` is accepted for WebSocket auth; URLs may be logged (proxy, access logs).
- **Impact:** Token leakage if URLs are logged.
- **Fix:** Remove query‑param support; rely on cookie (browser) or `Authorization` header (service clients).

---

## 3. Medium‑Priority Findings

### 3.1. No org‑existence validation for `X-Organization-Id`
- **Location:** `api/src/core/auth.py:get_execution_context`.
- **Issue:** Header is parsed and used as UUID but not verified against database.
- **Impact:** Platform admin could operate on a non‑existent org ID (edge case).
- **Fix:** Validate org exists before using it (optional; adds DB hit).

### 3.2. MFA‑bypass for OAuth users
- **Design decision:** OAuth users bypass MFA (provider is trusted). This is reasonable but should be documented and perhaps configurable.

### 3.3. Hard‑coded Fernet salt
- **Location:** `api/src/core/security.py:_get_fernet_key`.
- **Issue:** Fixed salt `b"bifrost_secrets_v1"` reduces key derivation entropy.
- **Impact:** If secret key is weak, derived encryption key may be weaker.
- **Fix:** Use per‑secret random salt stored with encrypted data; or derive key via HKDF.

### 3.4. No rate limiting on login/refresh endpoints
- **Issue:** No protection against brute‑force password guessing or token‑refresh abuse.
- **Fix:** Add IP‑based rate limiting (e.g., via Redis) for `/auth/login`, `/auth/refresh`, `/auth/mfa/*`.

### 3.5. Legacy fallback for tokens without embedded claims
- **Location:** `api/src/core/auth.py:get_current_user_optional` (lines 168‑187).
- **Issue:** Tokens without `email`/`user_type` claims fall back to DB lookup; roles are empty.
- **Impact:** Legacy tokens still work but have reduced functionality.
- **Fix:** Consider deprecating legacy token format; ensure all new tokens include claims.

---

## 4. Recommendations (Implementation Order)

### 4.1. Immediate (Critical)
1. **Token‑type enforcement:**
   - Add `type="access"` to `create_access_token`.
   - In `get_current_user_optional`/`get_current_user`, reject tokens where `payload.get("type") != "access"`.
   - Apply same check in WebSocket auth.

2. **Remove/disable `/auth/oauth/login`:**
   - Delete route or feature‑flag it off.
   - Use only `/auth/oauth/callback` (which exchanges code + verifier).

3. **OAuth callback hardening:**
   - Store `state` in Redis (or signed cookie) and validate on callback.
   - Bind PKCE verifier to state (store or sign); recompute challenge on callback.

4. **Refresh rotation & revocation:**
   - Add `jti` and `iat` to refresh tokens.
   - Redis key: `refresh_jti:{user_id}:{jti}` with TTL = refresh token expiry.
   - On `/auth/refresh`: verify JTI exists, delete it, issue new refresh token with new JTI.
   - Add `/auth/revoke` (self) and `/admin/users/{id}/revoke` endpoints.

### 4.2. Short‑term (High‑impact)
5. **CSRF protection:**
   - Generate CSRF token on session start, set as `HttpOnly` cookie.
   - Require `X-CSRF-Token` header on unsafe methods (POST, PUT, DELETE, PATCH) when cookie auth is used.
   - Reject mismatched/absent header.

6. **JWT issuer/audience:**
   - Add `iss` and `aud` claims when issuing.
   - Validate in `decode_token`; log failures.

7. **Remove WebSocket query‑param auth:**
   - Delete the `?token=` fallback in `get_current_user_ws`.
   - Accept only cookie (`access_token`) or `Authorization` header.

8. **Rate limiting:**
   - Add Redis‑based sliding‑window rate limiter for auth endpoints.

### 4.3. Medium‑term (Robustness)
9. **Org‑validation and auditing:**
   - Validate org exists when `X-Organization-Id` is used.
   - Log cross‑org access (user, target org) for audit trail.

10. **Fernet key derivation improvement:**
    - Use HKDF with random salt; store salt alongside encrypted data.
    - Or migrate to dedicated secret‑management (Azure Key Vault, HashiCorp Vault).

11. **MFA configuration:**
    - Make OAuth MFA‑bypass configurable per provider.
    - Add option to require MFA even for OAuth.

12. **Legacy token cleanup:**
    - Add migration to re‑issue all tokens with embedded claims.
    - After migration, remove DB fallback path.

---

## 5. Testing Strategy

Add regression tests for each fixed issue:

1. **Token‑type enforcement:**
   - Refresh token in `Authorization` header → 401.
   - Access token with `type="access"` → 200.

2. **OAuth callback:**
   - Missing/invalid state → 400.
   - Mismatched PKCE verifier → 400.

3. **Refresh rotation:**
   - Old JTI rejected after refresh.
   - Revoke‑all → subsequent refresh fails.

4. **CSRF protection:**
   - Cookie‑auth’d POST without CSRF header → 403.
   - Valid CSRF header → 200.

5. **WebSocket auth:**
   - Query param `?token=` → rejected (connection closed).
   - Cookie or Authorization header → accepted.

6. **Rate limiting:**
   - Exceed limit → 429.
   - Limit resets after window.

---

## 6. Files Requiring Changes

| File | Purpose | Changes |
|------|---------|---------|
| `api/src/core/security.py` | JWT creation/decoding | Add `type`, `iss`, `aud` claims; validate in decode. |
| `api/src/core/auth.py` | Auth dependencies, WS auth | Reject refresh tokens; remove query‑param fallback. |
| `api/src/routers/auth.py` | Auth endpoints | Remove `/auth/oauth/login`; add CSRF middleware. |
| `api/src/routers/oauth_sso.py` | OAuth endpoints | Validate state; store/bind PKCE verifier. |
| `api/src/config.py` | Settings | Add CSRF secret, rate‑limit config. |
| `api/shared/cache.py` | Redis helpers | Add JTI storage, rate‑limit counters. |
| `api/tests/unit/test_auth.py` | Unit tests | Add security regression tests. |
| `api/tests/integration/test_oauth.py` | Integration tests | Test OAuth flow with state/PKCE. |

---

## 7. FAQ

### Why remove `/auth/oauth/login`?
It’s an unauthenticated endpoint that issues full JWTs based on client‑supplied email—a trivial account‑takeover path. The correct flow is frontend → OAuth provider → `/auth/oauth/callback` with code + verifier.

### Why enforce `type="access"`? Isn’t a valid token enough?
Refresh tokens have longer TTL and are meant for a single purpose: obtaining new access tokens. Allowing them as bearer tokens extends their privilege and lifetime beyond intended scope. Strict separation is a security best practice.

### Can we keep `SameSite=Lax` and skip CSRF tokens?
`SameSite=Lax` blocks cross‑site POSTs, but any unsafe GET endpoints remain vulnerable. If your API has no state‑changing GETs, you could rely on `SameSite=Strict` (blocks all cross‑site requests). Adding CSRF tokens is a defense‑in‑depth measure that also protects against same‑site attacks (e.g., subdomain hijacking).

### Should we add a JWT blacklist?
Not necessary if you implement refresh‑token rotation with JTI storage. Access tokens are short‑lived (30m); revoking them individually is rarely needed. If immediate revocation is required, use a short‑lived blacklist (Redis) for JTIs of revoked access tokens (optional).

### Is PKCE still secure if verifier is client‑side?
Yes, PKCE is designed for public clients (no client secret). The security relies on the verifier being held by the same client that initiated the flow. However, binding the verifier to the server‑side state prevents tampering if the state is compromised.

### What about API‑key authentication for service‑to‑service?
Currently, only user JWTs and cookies are supported. For future service‑to‑service, consider adding API‑key authentication (X‑API‑Key header) with separate scope/rate limits, stored hashed in DB.

---

## 8. Summary

The current authentication implementation follows common FastAPI patterns but has several critical security gaps that must be addressed before production deployment. The highest‑priority fixes are:

1. **Separate access and refresh tokens** (type enforcement).
2. **Remove the unsafe OAuth login endpoint.**
3. **Harden OAuth flow with state validation and server‑side PKCE binding.**
4. **Implement refresh‑token rotation and revocation.**
5. **Add CSRF protection for cookie‑based auth.**

These changes will bring the authentication system to a production‑ready state, providing strong protection against token misuse, CSRF, OAuth tampering, and account takeover.

---
**Review completed:** 2025-12-05  
**Next steps:** Implement fixes in order of criticality; add regression tests; re‑review after changes.