# Security Policies Documentation

This document outlines all security policies implemented in the microservices FastAPI template.

## Overview

The application implements multiple layers of security to protect against common web vulnerabilities and attacks. All security features are configurable through `config/settings/settings.toml`.

## Implemented Security Policies

### 1. Security Headers Middleware

Adds comprehensive security headers to all HTTP responses to protect against various attacks.

#### Headers Implemented:

- **X-Content-Type-Options: nosniff**
  - Prevents MIME type sniffing attacks
  - Forces browsers to respect declared content types

- **X-Frame-Options: DENY**
  - Prevents clickjacking attacks
  - Options: `DENY`, `SAMEORIGIN`, `ALLOW-FROM`
  - Configurable via `security.X_FRAME_OPTIONS`

- **X-XSS-Protection: 1; mode=block**
  - Enables browser XSS filter (legacy support)
  - Configurable via `security.X_XSS_PROTECTION`

- **Strict-Transport-Security (HSTS)**
  - Forces HTTPS connections
  - Prevents protocol downgrade attacks
  - Configurable via `security.ENABLE_HSTS`, `security.HSTS_MAX_AGE`, etc.
  - Default: Enabled in production, disabled in development

- **Content-Security-Policy (CSP)**
  - Controls which resources can be loaded
  - Prevents XSS and data injection attacks
  - Configurable via `security.CONTENT_SECURITY_POLICY`
  - Example: `"default-src 'self'; script-src 'self'"`

- **Referrer-Policy: strict-origin-when-cross-origin**
  - Controls referrer information sent with requests
  - Configurable via `security.REFERRER_POLICY`

- **Permissions-Policy**
  - Controls browser features (geolocation, camera, microphone, etc.)
  - Configurable via `security.PERMISSIONS_POLICY`
  - Example: `"geolocation=(), microphone=(), camera=()"`

- **Cross-Origin Policies**
  - `Cross-Origin-Opener-Policy: same-origin`
  - `Cross-Origin-Resource-Policy: same-origin`
  - `Cross-Origin-Embedder-Policy` (optional)
  - Prevents cross-origin attacks

### 2. Rate Limiting Middleware

Prevents abuse and DDoS attacks by limiting the number of requests per IP address.

#### Features:

- **In-memory rate limiting** (per IP address)
- **Configurable rate limits** via `security.RATE_LIMIT_REQUESTS_PER_MINUTE`
- **Rate limit headers** in responses:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `Retry-After`: Seconds to wait before retrying (when limit exceeded)

#### Configuration:

```toml
[security]
ENABLE_RATE_LIMITING = true
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
```

#### Response on Rate Limit Exceeded:

- Status Code: `429 Too Many Requests`
- Headers: `Retry-After: 60`
- Body: Error message with rate limit details

#### Note:

For production with multiple workers, consider using Redis-based rate limiting for distributed rate limiting across instances.

### 3. Request Size Limiting Middleware

Prevents large payload attacks by limiting request body size.

#### Features:

- **Content-Length validation** before processing
- **Configurable size limit** via `security.MAX_REQUEST_SIZE_MB`
- **Early rejection** of oversized requests

#### Configuration:

```toml
[security]
MAX_REQUEST_SIZE_MB = 10  # 10MB default
```

#### Response on Size Limit Exceeded:

- Status Code: `413 Payload Too Large`
- Body: Error message with size limit details

### 4. Trusted Host Middleware

Validates the `Host` header to prevent host header injection attacks.

#### Features:

- **Host header validation** against allowed hosts
- **Wildcard support** (e.g., `*.example.com`)
- **Configurable** via `settings.ALLOWED_HOSTS`

#### Configuration:

```toml
ALLOWED_HOSTS = ["your-domain.com", "*.your-domain.com"]
```

### 5. CORS (Cross-Origin Resource Sharing)

Controls which origins can access the API.

#### Features:

- **Origin validation** against allowed origins
- **Credential handling** (prevents wildcard + credentials)
- **Method and header restrictions**
- **Configurable** via `settings.CORS_ORIGINS` and `settings.cors.*`

#### Security Note:

The middleware automatically disables credentials when wildcard origins (`*`) are used, as this is a security risk.

### 6. Request ID Tracking

Adds unique request IDs for tracing and debugging.

#### Features:

- **Unique request ID** per request (`X-Request-ID` header)
- **Request tracing** in logs
- **Correlation** across services

## Configuration

All security settings are configured in `config/settings/settings.toml`:

```toml
[security]
# HSTS (HTTP Strict Transport Security)
ENABLE_HSTS = false  # Set to true in production
HSTS_MAX_AGE = 31536000  # 1 year in seconds
HSTS_INCLUDE_SUBDOMAINS = true
HSTS_PRELOAD = false

# Security Headers
X_FRAME_OPTIONS = "DENY"
X_XSS_PROTECTION = "1; mode=block"
REFERRER_POLICY = "strict-origin-when-cross-origin"
CROSS_ORIGIN_OPENER_POLICY = "same-origin"
CROSS_ORIGIN_RESOURCE_POLICY = "same-origin"

# Content Security Policy (optional)
# CONTENT_SECURITY_POLICY = "default-src 'self'; script-src 'self'"

# Permissions Policy (optional)
# PERMISSIONS_POLICY = "geolocation=(), microphone=(), camera=()"

# Rate Limiting
ENABLE_RATE_LIMITING = true
RATE_LIMIT_REQUESTS_PER_MINUTE = 60

# Request Size Limits
MAX_REQUEST_SIZE_MB = 10
```

### Environment-Specific Configuration

Settings can be overridden per environment:

```toml
[production.security]
ENABLE_HSTS = true
RATE_LIMIT_REQUESTS_PER_MINUTE = 100

[development.security]
ENABLE_RATE_LIMITING = false  # Disable for easier testing
MAX_REQUEST_SIZE_MB = 50  # Larger limit for development
```

## Additional Security Recommendations

### 1. Authentication & Authorization

- Implement JWT token validation
- Use OAuth2/OIDC for user authentication
- Implement role-based access control (RBAC)
- Validate API keys for service-to-service communication

### 2. Input Validation

- Use Pydantic models for all request/response validation
- Sanitize user inputs
- Validate file uploads (type, size, content)
- Use parameterized queries (already handled by SQLAlchemy)

### 3. Database Security

- Use connection pooling with limits
- Implement query timeouts
- Use read-only database users where possible
- Encrypt sensitive data at rest
- Use parameterized queries (SQLAlchemy handles this)

### 4. Logging & Monitoring

- Log all authentication attempts
- Log security-related events (rate limit exceeded, large requests, etc.)
- Monitor for suspicious patterns
- Set up alerts for security events

### 5. API Security

- Implement API versioning
- Use API keys for service-to-service communication
- Implement request signing for critical operations
- Add request/response encryption for sensitive data

### 6. Infrastructure Security

- Use HTTPS/TLS everywhere
- Implement network segmentation
- Use firewall rules to restrict access
- Keep dependencies updated (use `pip-audit` or `safety`)
- Use secrets management (e.g., HashiCorp Vault, AWS Secrets Manager)

### 7. Additional Middleware to Consider

- **IP Whitelisting/Blacklisting**: Control access by IP address
- **Request Sanitization**: Clean and validate all inputs
- **API Key Validation**: Validate API keys for service-to-service calls
- **Request Signing**: Verify request signatures for critical operations
- **Distributed Rate Limiting**: Use Redis for rate limiting across multiple instances

## Testing Security

### Manual Testing

1. **Security Headers**: Check response headers using browser dev tools or `curl`
2. **Rate Limiting**: Send multiple requests quickly to test rate limits
3. **Request Size**: Try sending a request larger than the limit
4. **CORS**: Test from different origins

### Automated Testing

Consider adding security tests:

```python
def test_security_headers(client):
    response = client.get("/")
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"

def test_rate_limiting(client):
    # Send requests exceeding the limit
    for _ in range(61):
        response = client.get("/")
    assert response.status_code == 429
```

## Security Checklist

- [x] Security headers middleware
- [x] Rate limiting
- [x] Request size limiting
- [x] Trusted host validation (HTTPS redirect handled by nginx/reverse proxy)
- [x] CORS configuration
- [x] Request ID tracking
- [ ] Authentication middleware (to be implemented)
- [ ] API key validation (to be implemented)
- [ ] IP whitelisting/blacklisting (to be implemented)
- [ ] Request sanitization (to be implemented)
- [ ] Distributed rate limiting with Redis (to be implemented)

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Mozilla Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/advanced/security/)
