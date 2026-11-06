# Redis + Redis Insight

Standalone Redis and Redis Insight UI for local development.

## Usage

From project root:

```bash
docker compose -f docker/redis/docker-compose.yml up -d
```

## Endpoints

| Service       | URL / Connection        |
|---------------|-------------------------|
| Redis         | `localhost:6379`        |
| Redis Insight | http://localhost:5540  |

In Redis Insight: add database with host `redis` (inside Docker) or `host.docker.internal` / `localhost` (from host), port `6379`, no password unless you add one.

## Django (cache/sessions)

To use Redis as Django cache, set in settings (e.g. production or local override):

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}
```

Requires the `redis` Python package.
