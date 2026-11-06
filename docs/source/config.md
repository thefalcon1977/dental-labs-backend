# Configuration Reference

This document explains all acceptable values for configuration files. The project uses Dynaconf for configuration management with a hierarchical priority system.

## Configuration Priority

Configuration values are loaded in this order (highest priority first):

1. **Environment Variables** (with `APP_` prefix)
2. **`.env` File** (with `APP_` prefix)
3. **Environment-Specific TOML** (e.g., `settings.production.toml`)
4. **Base `settings.toml`** (default values)

## Section 1: .env File Values

The `.env` file is used for local development and should never be committed to version control. All environment variables must use the `APP_` prefix and use double underscores (`__`) for nested configuration.

### Important: No Duplication Rule

**If a configuration setting is defined in `.env` file, it should NOT be defined in `settings.toml` (and vice versa).**

- **`.env` file**: Use for environment-specific overrides, secrets, and local development values
- **`settings.toml`**: Use for default values and application-level configuration
- **Priority**: Environment variables (`.env` or OS) always override `settings.toml` values
- **Best Practice**: Keep defaults in `settings.toml`, override with `.env` when needed

### Application Settings

| Variable | Type | Required | Default | Acceptable Values | Description |
|----------|------|----------|---------|-------------------|-------------|
| `APP_SECRET_KEY` | string | Yes | - | Minimum 32 characters | Application secret key for encryption/signing |
| `APP_SERVICE_NAME` | string | No | `microservice-fastapi-template` | Any string | Service name for logging and identification |
| `APP_DEBUG` | boolean | Yes | `true` | `true`, `false` | Enable debug mode (detailed errors, auto-reload) |
| `APP_LOG_LEVEL` | string | Yes | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Logging verbosity level |
| `APP_ENABLE_METRICS` | boolean | Yes | `true` | `true`, `false` | Enable Prometheus metrics endpoint |
| `APP_DEFAULT_TIMEZONE` | string | Yes | `UTC` | IANA timezone string (e.g., `UTC`, `America/New_York`) | Default timezone for the application |
| `APP_HOST` | string | Yes | `0.0.0.0` | IP address or hostname | Server bind address |
| `APP_PORT` | integer | Yes | `8000` | `1` to `65535` | Server port number |
| `APP_ALLOWED_HOSTS` | list | Yes | `["*"]` | List of hostnames or `["*"]` for all | Allowed host headers (security) |

### CORS Configuration

| Variable | Type | Required | Default | Acceptable Values | Description |
|----------|------|----------|---------|-------------------|-------------|
| `APP_CORS__ORIGINS` | list | Yes | `["*"]` | List of URLs or `["*"]` for all | CORS allowed origins |
| `APP_CORS__ALLOW_CREDENTIALS` | boolean | No | `true` | `true`, `false` | Allow credentials in CORS requests |
| `APP_CORS__ALLOWED_METHODS` | list | No | `["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]` | List of HTTP methods | Allowed HTTP methods for CORS |
| `APP_CORS__ALLOWED_HEADERS` | list | No | Default headers list | List of header names | Allowed request headers |
| `APP_CORS__EXPOSED_HEADERS` | list | No | `["X-Request-ID", "X-Process-Time", ...]` | List of header names | Headers exposed to client |
| `APP_CORS__MAX_AGE` | integer | No | `3600` | `0` or positive integer | CORS preflight cache duration (seconds) |

### Security Configuration

| Variable | Type | Required | Default | Acceptable Values | Description |
|----------|------|----------|---------|-------------------|-------------|
| `APP_SECURITY__ENABLE_HSTS` | boolean | No | `false` | `true`, `false` | Enable HTTP Strict Transport Security |
| `APP_SECURITY__HSTS_MAX_AGE` | integer | No | `31536000` | `0` or positive integer | HSTS max-age in seconds (1 year = 31536000) |
| `APP_SECURITY__HSTS_INCLUDE_SUBDOMAINS` | boolean | No | `true` | `true`, `false` | Include subdomains in HSTS |
| `APP_SECURITY__HSTS_PRELOAD` | boolean | No | `false` | `true`, `false` | Enable HSTS preload (production) |
| `APP_SECURITY__X_FRAME_OPTIONS` | string | No | `DENY` | `DENY`, `SAMEORIGIN`, `ALLOW-FROM <uri>` | X-Frame-Options header value |
| `APP_SECURITY__X_XSS_PROTECTION` | string | No | `1; mode=block` | `0`, `1`, `1; mode=block` | X-XSS-Protection header value |
| `APP_SECURITY__REFERRER_POLICY` | string | No | `strict-origin-when-cross-origin` | `no-referrer`, `strict-origin`, `strict-origin-when-cross-origin`, etc. | Referrer-Policy header value |
| `APP_SECURITY__CROSS_ORIGIN_OPENER_POLICY` | string | No | `same-origin` | `same-origin`, `same-origin-allow-popups`, `unsafe-none` | Cross-Origin-Opener-Policy header |
| `APP_SECURITY__CROSS_ORIGIN_RESOURCE_POLICY` | string | No | `same-origin` | `same-origin`, `cross-origin`, `same-site` | Cross-Origin-Resource-Policy header |
| `APP_SECURITY__ENABLE_RATE_LIMITING` | boolean | No | `true` | `true`, `false` | Enable rate limiting middleware |
| `APP_SECURITY__RATE_LIMIT_REQUESTS_PER_MINUTE` | integer | No | `60` | Positive integer (`>= 1`) | Maximum requests per minute per client |
| `APP_SECURITY__MAX_REQUEST_SIZE_MB` | integer | No | `10` | Positive integer (`>= 1`) | Maximum request body size in megabytes |

### Logging Configuration

| Variable | Type | Required | Default | Acceptable Values | Description |
|----------|------|----------|---------|-------------------|-------------|
| `APP_LOGGING__SQLALCHEMY_LOG_LEVEL` | string | No | `WARNING` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | SQLAlchemy log verbosity |
| `APP_LOGGING__STARTUP_INFO_MODE` | string | No | `full` | `full`, `minimal`, `off` | Startup info verbosity |

### Database Configuration

| Variable | Type | Required | Default | Acceptable Values | Description |
|----------|------|----------|---------|-------------------|-------------|
| `APP_DATABASE__ENABLED` | boolean | No | `false` | `true`, `false` | Enable database features |
| `APP_DATABASE__DRIVER` | string | No | `postgresql+asyncpg` | `postgresql+asyncpg` | Database driver (currently only PostgreSQL) |
| `APP_DATABASE__HOST` | string | No | `localhost` | Hostname or IP address | Database server host (use service name in Docker) |
| `APP_DATABASE__PORT` | integer | No | `5432` | `1` to `65535` | Database server port |
| `APP_DATABASE__NAME` | string | No | `app_db` | Database name | Database name |
| `APP_DATABASE__USER` | string | No | `postgres` | Username | Database username |
| `APP_DATABASE__PASSWORD` | string | No | `postgres` | Password string | Database password (use environment variable in production) |
| `APP_DATABASE__POOL_SIZE` | integer | No | `5` | Positive integer (`>= 1`) | Connection pool size |
| `APP_DATABASE__MAX_OVERFLOW` | integer | No | `10` | Non-negative integer (`>= 0`) | Additional connections beyond pool size |
| `APP_DATABASE__POOL_PRE_PING` | boolean | No | `true` | `true`, `false` | Test connections before use |
| `APP_DATABASE__POOL_RECYCLE` | integer | No | `3600` | Positive integer (`>= 1`) | Connection recycle time in seconds |
| `APP_DATABASE__POOL_TIMEOUT` | integer | No | `30` | Positive integer (`>= 1`) | Connection timeout in seconds |
| `APP_DATABASE__ECHO` | boolean | No | `false` | `true`, `false` | Echo SQL queries (debug only) |

### Redis Configuration

| Variable | Type | Required | Default | Acceptable Values | Description |
|----------|------|----------|---------|-------------------|-------------|
| `APP_REDIS__ENABLED` | boolean | No | `false` | `true`, `false` | Enable Redis features |
| `APP_REDIS__HOST` | string | No | `localhost` | Hostname or IP address | Redis server host |
| `APP_REDIS__PORT` | integer | No | `6379` | `1` to `65535` | Redis server port |
| `APP_REDIS__DB` | integer | No | `0` | Non-negative integer (`>= 0`) | Redis database number |
| `APP_REDIS__PASSWORD` | string | No | `""` | Password string or empty | Redis password (empty if no auth) |
| `APP_REDIS__SSL` | boolean | No | `false` | `true`, `false` | Enable SSL/TLS for Redis |
| `APP_REDIS__SOCKET_TIMEOUT` | integer | No | `5` | Positive integer (`>= 1`) | Socket timeout in seconds |
| `APP_REDIS__SOCKET_CONNECT_TIMEOUT` | integer | No | `5` | Positive integer (`>= 1`) | Connection timeout in seconds |
| `APP_REDIS__RETRY_ON_TIMEOUT` | boolean | No | `true` | `true`, `false` | Retry on timeout errors |
| `APP_REDIS__MAX_CONNECTIONS` | integer | No | `50` | Positive integer (`>= 1`) | Maximum Redis connections |

### Keycloak Configuration

| Variable | Type | Required | Default | Acceptable Values | Description |
|----------|------|----------|---------|-------------------|-------------|
| `APP_KEYCLOAK__SERVER_URL` | string | No | `http://localhost:8080` | Full URL (http/https) | Keycloak server URL |
| `APP_KEYCLOAK__REALM` | string | No | `master` | Realm name | Keycloak realm name |
| `APP_KEYCLOAK__CLIENT_ID` | string | No | `your-client-id` | Client ID string | Keycloak client ID |
| `APP_KEYCLOAK__CLIENT_SECRET` | string | No | `your-client-secret` | Client secret string | Keycloak client secret (use env var in production) |
| `APP_KEYCLOAK__ADMIN_USERNAME` | string | No | `admin` | Username | Keycloak admin username |
| `APP_KEYCLOAK__ADMIN_PASSWORD` | string | No | `admin` | Password | Keycloak admin password (use env var in production) |

### Uvicorn Configuration

| Variable | Type | Required | Default | Acceptable Values | Description |
|----------|------|----------|---------|-------------------|-------------|
| `APP_UVICORN__WORKERS` | integer | No | `1` | Positive integer (`>= 1`) | Number of worker processes |
| `APP_UVICORN__WORKERS_MAX` | integer | No | `4` | Positive integer (`>= 1`) | Maximum allowed workers |
| `APP_UVICORN__WORKER_CLASS` | string | No | `uvicorn.workers.UvicornWorker` | Worker class path | Uvicorn worker class |
| `APP_UVICORN__TIMEOUT_KEEP_ALIVE` | integer | No | `5` | Positive integer (`>= 1`) | Keep-alive timeout in seconds |
| `APP_UVICORN__LIMIT_CONCURRENCY` | integer | No | `1000` | Positive integer (`>= 1`) | Maximum concurrent connections |
| `APP_UVICORN__LIMIT_MAX_REQUESTS` | integer | No | `10000` | Positive integer (`>= 1`) | Maximum requests per worker before restart |
| `APP_UVICORN__LIMIT_MAX_REQUESTS_JITTER` | integer | No | `1000` | Non-negative integer (`>= 0`) | Random jitter added to max requests to stagger worker restarts |
| `APP_UVICORN__BACKLOG` | integer | No | `2048` | Positive integer (`>= 1`) | Connection backlog size |

### Environment Variable

| Variable | Type | Required | Default | Acceptable Values | Description |
|----------|------|----------|---------|-------------------|-------------|
| `ENV` | string | No | `development` | `development`, `production`, `testing` | Active environment name |

### Notes for .env File

#### Naming Pattern (IMPORTANT)

**All nested configuration MUST use double underscores (`__`) to separate section from setting:**

- ✅ **Correct**: `APP_DATABASE__HOST`, `APP_CORS__ALLOW_CREDENTIALS`, `APP_SECURITY__ENABLE_HSTS`
- ❌ **Incorrect**: `APP_DATABASE_HOST`, `APP_CORS_ALLOW_CREDENTIALS`, `APP_SECURITY_ENABLE_HSTS`

**Top-level settings use single underscores as part of the variable name (not for nesting):**

- ✅ **Correct**: `APP_SECRET_KEY`, `APP_LOG_LEVEL`, `APP_ENABLE_METRICS`, `APP_CORS__ORIGINS`
- These are top-level settings, so the single underscore is part of the name, not a separator

**Pattern Summary:**
- **Top-level**: `APP_SETTING_NAME` (single underscore is part of the name)
- **Nested**: `APP_SECTION__SETTING` (double underscore separates section from setting)

#### Other Notes

- **Lists**: Use comma-separated values or JSON array format (e.g., `["item1", "item2"]`)
- **Booleans**: Use `true` or `false` (lowercase)
- **Never Commit**: The `.env` file should be in `.gitignore` and never committed
- **Docker**: In Docker, use service names for database/Redis hosts (e.g., `postgres` instead of `localhost`)
- **Secret Key**: Generate a secure secret key using `python manage.py generate-secret-key`

## Section 2: settings.toml Values

The `settings.toml` file contains default configuration values and is organized into sections. Values can be overridden by environment variables or environment-specific TOML files.

### Important: No Duplication Rule

**If a configuration setting is defined in `.env` file, it should NOT be defined in `settings.toml` (and vice versa).**

- **`settings.toml`**: Use for default values and application-level configuration
- **`.env` file**: Use for environment-specific overrides, secrets, and local development values
- **Priority**: Environment variables (`.env` or OS) always override `settings.toml` values
- **Best Practice**: Keep defaults in `settings.toml`, override with `.env` when needed

### File Structure

The file uses TOML format with sections:
- `[default]` - Base configuration values
- `[development]` - Development environment overrides
- `[production]` - Production environment overrides
- `[testing]` - Testing environment overrides
- `[section_name]` - Configuration sections (cors, security, database, etc.)

### Application Settings Section

All values in the `[default]` section:

| Setting | Type | Required | Default | Acceptable Values | Description |
|---------|------|----------|---------|-------------------|-------------|
| `SERVICE_NAME` | string | No | `microservices-fastapi-template` | Any string | Service name |
| `DEBUG` | boolean | Yes | `true` | `true`, `false` | Debug mode |
| `LOG_LEVEL` | string | Yes | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Log level |
| `ENABLE_METRICS` | boolean | Yes | `true` | `true`, `false` | Enable metrics |
| `DEFAULT_TIMEZONE` | string | Yes | `UTC` | IANA timezone string | Default timezone |
| `HOST` | string | Yes | `0.0.0.0` | IP address or hostname | Server host |
| `PORT` | integer | Yes | `8000` | `1` to `65535` | Server port |
| `ALLOWED_HOSTS` | array | Yes | `["*"]` | Array of strings or `["*"]` | Allowed hosts |

### CORS Section `[cors]`

| Setting | Type | Required | Default | Acceptable Values | Description |
|---------|------|----------|---------|-------------------|-------------|
| `ORIGINS` | array | Yes | `["*"]` | Array of URLs or `["*"]` | CORS allowed origins |
| `ALLOW_CREDENTIALS` | boolean | No | `true` | `true`, `false` | Allow credentials |
| `ALLOWED_METHODS` | array | No | `["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]` | Array of HTTP method strings | Allowed methods |
| `ALLOWED_HEADERS` | array | No | Default header list | Array of header name strings | Allowed headers |
| `EXPOSED_HEADERS` | array | No | `["X-Request-ID", "X-Process-Time", ...]` | Array of header name strings | Exposed headers |
| `MAX_AGE` | integer | No | `3600` | `0` or positive integer | Preflight cache (seconds) |

### Security Section `[security]`

| Setting | Type | Required | Default | Acceptable Values | Description |
|---------|------|----------|---------|-------------------|-------------|
| `ENABLE_HSTS` | boolean | No | `false` | `true`, `false` | Enable HSTS |
| `HSTS_MAX_AGE` | integer | No | `31536000` | `0` or positive integer | HSTS max-age (seconds) |
| `HSTS_INCLUDE_SUBDOMAINS` | boolean | No | `true` | `true`, `false` | Include subdomains |
| `HSTS_PRELOAD` | boolean | No | `false` | `true`, `false` | HSTS preload |
| `X_FRAME_OPTIONS` | string | No | `DENY` | `DENY`, `SAMEORIGIN`, `ALLOW-FROM <uri>` | X-Frame-Options |
| `X_XSS_PROTECTION` | string | No | `1; mode=block` | `0`, `1`, `1; mode=block` | X-XSS-Protection |
| `REFERRER_POLICY` | string | No | `strict-origin-when-cross-origin` | Valid referrer policy string | Referrer-Policy |
| `CROSS_ORIGIN_OPENER_POLICY` | string | No | `same-origin` | `same-origin`, `same-origin-allow-popups`, `unsafe-none` | COOP header |
| `CROSS_ORIGIN_RESOURCE_POLICY` | string | No | `same-origin` | `same-origin`, `cross-origin`, `same-site` | CORP header |
| `ENABLE_RATE_LIMITING` | boolean | No | `true` | `true`, `false` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | integer | No | `60` | Positive integer (`>= 1`) | Rate limit per minute |
| `MAX_REQUEST_SIZE_MB` | integer | No | `10` | Positive integer (`>= 1`) | Max request size (MB) |

### Logging Section `[logging]`

| Setting | Type | Required | Default | Acceptable Values | Description |
|---------|------|----------|---------|-------------------|-------------|
| `SQLALCHEMY_LOG_LEVEL` | string | No | `WARNING` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | SQLAlchemy log verbosity |
| `STARTUP_INFO_MODE` | string | No | `full` | `full`, `minimal`, `off` | Startup info verbosity |

### Database Section `[database]`

| Setting | Type | Required | Default | Acceptable Values | Description |
|---------|------|----------|---------|-------------------|-------------|
| `ENABLED` | boolean | No | `false` | `true`, `false` | Enable database |
| `DRIVER` | string | No | `postgresql+asyncpg` | `postgresql+asyncpg` | Database driver |
| `HOST` | string | No | `localhost` | Hostname or IP | Database host |
| `PORT` | integer | No | `5432` | `1` to `65535` | Database port |
| `NAME` | string | No | `app_db` | Database name | Database name |
| `USER` | string | No | `postgres` | Username | Database user |
| `PASSWORD` | string | No | `postgres` | Password | Database password (development only) |
| `POOL_SIZE` | integer | No | `5` | Positive integer (`>= 1`) | Pool size |
| `MAX_OVERFLOW` | integer | No | `10` | Non-negative integer (`>= 0`) | Max overflow |
| `POOL_PRE_PING` | boolean | No | `true` | `true`, `false` | Pre-ping connections |
| `POOL_RECYCLE` | integer | No | `3600` | Positive integer (`>= 1`) | Recycle time (seconds) |
| `POOL_TIMEOUT` | integer | No | `30` | Positive integer (`>= 1`) | Pool timeout (seconds) |
| `ECHO` | boolean | No | `false` | `true`, `false` | Echo SQL (debug) |

### Redis Section `[redis]`

| Setting | Type | Required | Default | Acceptable Values | Description |
|---------|------|----------|---------|-------------------|-------------|
| `ENABLED` | boolean | No | `false` | `true`, `false` | Enable Redis |
| `HOST` | string | No | `localhost` | Hostname or IP | Redis host |
| `PORT` | integer | No | `6379` | `1` to `65535` | Redis port |
| `DB` | integer | No | `0` | Non-negative integer (`>= 0`) | Redis database number |
| `PASSWORD` | string | No | `""` | Password or empty string | Redis password |
| `SSL` | boolean | No | `false` | `true`, `false` | Enable SSL |
| `SOCKET_TIMEOUT` | integer | No | `5` | Positive integer (`>= 1`) | Socket timeout (seconds) |
| `SOCKET_CONNECT_TIMEOUT` | integer | No | `5` | Positive integer (`>= 1`) | Connect timeout (seconds) |
| `RETRY_ON_TIMEOUT` | boolean | No | `true` | `true`, `false` | Retry on timeout |
| `MAX_CONNECTIONS` | integer | No | `50` | Positive integer (`>= 1`) | Max connections |

### Keycloak Section `[keycloak]`

| Setting | Type | Required | Default | Acceptable Values | Description |
|---------|------|----------|---------|-------------------|-------------|
| `SERVER_URL` | string | No | `http://localhost:8080` | Full URL | Keycloak server URL |
| `REALM` | string | No | `master` | Realm name | Keycloak realm |
| `CLIENT_ID` | string | No | `your-client-id` | Client ID | Keycloak client ID |
| `CLIENT_SECRET` | string | No | `your-client-secret` | Client secret | Keycloak client secret |
| `ADMIN_USERNAME` | string | No | `admin` | Username | Admin username |
| `ADMIN_PASSWORD` | string | No | `admin` | Password | Admin password |

### Uvicorn Section `[uvicorn]`

| Setting | Type | Required | Default | Acceptable Values | Description |
|---------|------|----------|---------|-------------------|-------------|
| `WORKERS` | integer | No | `1` | Positive integer (`>= 1`) | Worker count |
| `WORKERS_MAX` | integer | No | `4` | Positive integer (`>= 1`) | Max workers |
| `WORKER_CLASS` | string | No | `uvicorn.workers.UvicornWorker` | Worker class path | Worker class |
| `TIMEOUT_KEEP_ALIVE` | integer | No | `5` | Positive integer (`>= 1`) | Keep-alive timeout (seconds) |
| `LIMIT_CONCURRENCY` | integer | No | `1000` | Positive integer (`>= 1`) | Max concurrent connections |
| `LIMIT_MAX_REQUESTS` | integer | No | `10000` | Positive integer (`>= 1`) | Max requests per worker |
| `LIMIT_MAX_REQUESTS_JITTER` | integer | No | `1000` | Non-negative integer (`>= 0`) | Random jitter added to max requests to stagger worker restarts |
| `BACKLOG` | integer | No | `2048` | Positive integer (`>= 1`) | Connection backlog |

### Environment-Specific Sections

You can override any setting in environment-specific sections:

- `[development]` - Development environment overrides
- `[production]` - Production environment overrides
- `[testing]` - Testing environment overrides

You can also create nested sections like:
- `[development.database]` - Development database overrides
- `[production.security]` - Production security overrides
- `[development.uvicorn]` - Development uvicorn overrides

### Notes for settings.toml

- **No Sensitive Data**: Never put passwords, secrets, or API keys in `settings.toml`
- **Development Defaults Only**: Sensitive values should have development defaults only
- **Environment Overrides**: Use environment-specific sections for non-sensitive overrides
- **Type Consistency**: Ensure types match between sections (boolean, integer, string, array)
- **Comments**: Use `#` for comments in TOML files
- **Arrays**: Use TOML array syntax: `["item1", "item2"]`
- **Booleans**: Use `true` or `false` (lowercase)

### Example settings.toml Structure

```toml
[default]
# Application defaults
DEBUG = true
LOG_LEVEL = "INFO"

[database]
ENABLED = false
POOL_SIZE = 5

[development]
DEBUG = true
LOG_LEVEL = "DEBUG"

[development.database]
POOL_SIZE = 5

[production]
DEBUG = false
LOG_LEVEL = "INFO"

[production.database]
POOL_SIZE = 20
MAX_OVERFLOW = 40
```

## Configuration Validation

All configuration values are validated on application startup using validators defined in `config/settings/validators.py`. Invalid values will cause the application to fail to start with a clear error message.

## Best Practices

1. **Use Environment Variables for Secrets**: Always use environment variables (`.env` or OS env) for passwords, secrets, and API keys
2. **Use settings.toml for Defaults**: Put non-sensitive defaults in `settings.toml`
3. **Environment-Specific Overrides**: Use environment-specific sections in `settings.toml` for non-sensitive overrides
4. **Never Commit Secrets**: Never commit `.env` files or real secrets in `settings.toml`
5. **Validate Configuration**: Run `python manage.py show-config` to verify your configuration
6. **Docker Considerations**: In Docker, use service names for database/Redis hosts, not `localhost`
