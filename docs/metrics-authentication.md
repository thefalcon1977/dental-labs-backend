# Metrics Authentication Guide

## Overview

The metrics endpoint (`/metrics`) supports authentication to restrict access to Prometheus metrics data. This is separate from user authentication and designed for system-to-system communication between monitoring tools (Prometheus, Grafana) and the application.

## Authentication Methods

Two authentication methods are supported:

1. **Basic Authentication** (recommended for Prometheus)
   - Username/password authentication
   - Standard HTTP Basic Auth
   - Compatible with Prometheus scraping configuration

2. **Bearer Token Authentication**
   - Static token authentication
   - Alternative to Basic Auth
   - Useful for custom integrations

## Configuration

### Environment Variables (Recommended)

Metrics authentication is configured via environment variables in `.env` files or environment-specific files (`envs/env.dev`, `envs/env.prod`). This keeps sensitive credentials out of version control.

**Development** (`envs/env.dev`):
```bash
# Metrics authentication disabled for easier development/testing
APP_METRICS__AUTH_ENABLED=false
APP_METRICS__AUTH_METHOD=basic
APP_METRICS__AUTH_USERNAME=prometheus
APP_METRICS__AUTH_PASSWORD=changeme-in-development
APP_METRICS__AUTH_BEARER_TOKEN=
```

**Production** (`envs/env.prod`):
```bash
# Enable authentication in production
APP_METRICS__AUTH_ENABLED=true
APP_METRICS__AUTH_METHOD=basic
APP_METRICS__AUTH_USERNAME=prometheus
# Set a strong password via environment variable or secrets management
APP_METRICS__AUTH_PASSWORD=your-secure-password-here-minimum-32-chars
APP_METRICS__AUTH_BEARER_TOKEN=
```

### Environment Variables (Direct)

```bash
# Enable metrics authentication
APP_METRICS__AUTH_ENABLED=true
APP_METRICS__AUTH_METHOD=basic
APP_METRICS__AUTH_USERNAME=prometheus
APP_METRICS__AUTH_PASSWORD=your-secure-password-here
```

Or for Bearer Token:

```bash
APP_METRICS__AUTH_ENABLED=true
APP_METRICS__AUTH_METHOD=bearer
APP_METRICS__AUTH_BEARER_TOKEN=your-secure-token-here
```

### Docker Compose Configuration

In `docker-compose.yml`:

```yaml
environment:
  APP_METRICS__AUTH_ENABLED: ${APP_METRICS__AUTH_ENABLED:-false}
  APP_METRICS__AUTH_METHOD: ${APP_METRICS__AUTH_METHOD:-basic}
  APP_METRICS__AUTH_USERNAME: ${APP_METRICS__AUTH_USERNAME:-prometheus}
  APP_METRICS__AUTH_PASSWORD: ${APP_METRICS__AUTH_PASSWORD:-changeme-in-production}
  APP_METRICS__AUTH_BEARER_TOKEN: ${APP_METRICS__AUTH_BEARER_TOKEN:-}
```

## Prometheus Configuration

### Basic Authentication

Configure Prometheus to use Basic Auth when scraping metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'fastapi-app'
    basic_auth:
      username: 'prometheus'
      password: 'your-secure-password-here'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['app:8000']
```

### Bearer Token Authentication

For Bearer Token authentication:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'fastapi-app'
    bearer_token: 'your-secure-token-here'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['app:8000']
```

### Using Prometheus Secrets

For production, use Prometheus secrets management:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'fastapi-app'
    basic_auth:
      username: 'prometheus'
      password_file: '/etc/prometheus/secrets/metrics_password'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['app:8000']
```

## Grafana Configuration

### Basic Authentication

When configuring Prometheus data source in Grafana:

1. Go to **Configuration** → **Data Sources** → **Add data source**
2. Select **Prometheus**
3. Enter Prometheus URL
4. Under **Auth**, enable **Basic Auth**
5. Enter username and password
6. Click **Save & Test**

### Bearer Token Authentication

For Bearer Token:

1. Go to **Configuration** → **Data Sources** → **Add data source**
2. Select **Prometheus**
3. Enter Prometheus URL
4. Under **Auth**, enable **Bearer Token**
5. Enter the token
6. Click **Save & Test**

**Note**: Grafana typically connects to Prometheus, not directly to the application metrics endpoint. Configure Prometheus with authentication as shown above, and Grafana will use Prometheus as the data source.

## Security Best Practices

### Production Recommendations

1. **Always enable authentication in production**
   ```toml
   [production.metrics]
   AUTH_ENABLED = true
   ```

2. **Use strong passwords/tokens**
   - Generate secure random passwords (minimum 32 characters)
   - Use environment variables or secrets management
   - Never commit passwords to version control

3. **Use HTTPS**
   - Always use HTTPS in production
   - Basic Auth credentials are sent in base64 (not encrypted)
   - HTTPS encrypts the entire connection

4. **Rotate credentials regularly**
   - Change metrics passwords/tokens periodically
   - Update Prometheus/Grafana configurations accordingly

5. **Restrict network access**
   - Use firewall rules to restrict access to metrics endpoint
   - Only allow Prometheus/Grafana servers to access `/metrics`
   - Consider using VPN or private networks

6. **Monitor access**
   - Log all metrics endpoint access attempts
   - Monitor for failed authentication attempts
   - Set up alerts for suspicious activity

### Development

For local development, authentication can be disabled:

```toml
[development.metrics]
AUTH_ENABLED = false
```

## Testing Authentication

### Test Basic Auth with curl

```bash
# Without authentication (should fail if enabled)
curl http://localhost:8000/metrics

# With Basic Auth
curl -u prometheus:your-password http://localhost:8000/metrics

# Or with explicit header
curl -H "Authorization: Basic $(echo -n 'prometheus:your-password' | base64)" \
  http://localhost:8000/metrics
```

### Test Bearer Token with curl

```bash
# With Bearer Token
curl -H "Authorization: Bearer your-token-here" \
  http://localhost:8000/metrics
```

## Troubleshooting

### Authentication Not Working

1. **Check configuration**
   - Verify `AUTH_ENABLED` is set correctly
   - Verify `AUTH_METHOD` matches your Prometheus configuration
   - Check username/password or token values

2. **Check logs**
   - Look for authentication-related log messages
   - Check for "Metrics access denied" warnings
   - Verify client IP addresses

3. **Test manually**
   - Use curl to test authentication
   - Verify credentials are correct
   - Check network connectivity

### Prometheus Scraping Fails

1. **Verify Prometheus configuration**
   - Check `basic_auth` or `bearer_token` configuration
   - Verify credentials match application settings
   - Check Prometheus logs for errors

2. **Check network**
   - Verify Prometheus can reach the application
   - Check firewall rules
   - Verify DNS resolution

3. **Verify endpoint**
   - Test `/metrics` endpoint manually
   - Check if authentication is required
   - Verify metrics are being generated

## Example: Complete Setup

### 1. Environment Configuration

**Development** (`envs/env.dev`):
```bash
APP_METRICS__AUTH_ENABLED=false
APP_METRICS__AUTH_METHOD=basic
APP_METRICS__AUTH_USERNAME=prometheus
APP_METRICS__AUTH_PASSWORD=changeme-in-development
```

**Production** (`envs/env.prod`):
```bash
APP_METRICS__AUTH_ENABLED=true
APP_METRICS__AUTH_METHOD=basic
APP_METRICS__AUTH_USERNAME=prometheus
APP_METRICS__AUTH_PASSWORD=secure-random-password-here-minimum-32-chars
```

### 2. Docker Compose

```yaml
services:
  app:
    environment:
      APP_METRICS__AUTH_ENABLED: "${APP_METRICS__AUTH_ENABLED:-false}"
      APP_METRICS__AUTH_METHOD: "${APP_METRICS__AUTH_METHOD:-basic}"
      APP_METRICS__AUTH_USERNAME: "${APP_METRICS__AUTH_USERNAME:-prometheus}"
      APP_METRICS__AUTH_PASSWORD: "${APP_METRICS__AUTH_PASSWORD:-changeme-in-production}"
```

### 3. Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'fastapi-app'
    basic_auth:
      username: 'prometheus'
      password_file: '/etc/prometheus/secrets/metrics_password'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['app:8000']
```

## Security Considerations

- **Separate from user authentication**: Metrics authentication is independent of user JWT authentication
- **System-to-system**: Designed for monitoring tools, not end users
- **No user context**: Metrics endpoint doesn't have user information
- **Read-only**: Metrics endpoint only returns data, no mutations
- **Rate limiting**: Consider rate limiting for metrics endpoint if needed
- **IP whitelisting**: Consider IP-based restrictions in addition to authentication

## Related Documentation

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
