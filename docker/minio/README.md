# MinIO (S3-compatible storage)

Standalone MinIO for local development.

## Usage

From project root:

```bash
docker compose -f docker/minio/docker-compose.yml up -d
```

## Endpoints

| Service   | URL (default)            |
|----------|---------------------------|
| S3 API   | http://localhost:9000     |
| Console  | http://localhost:9001     |

Login: `minioadmin` / `minioadmin` (override with `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`).

## Why was I redirected to the wrong port?

MinIO’s API can redirect the browser to the **console** port. It uses the port it sees (e.g. 9001 inside the container). If you map the console to a **different host port** (e.g. `MINIO_CONSOLE_PORT=10224`), the redirect can still point to `localhost:9001`, so the browser hits the wrong port and you get **connection refused**.

**Fix:** set `MINIO_BROWSER_REDIRECT_URL` to the URL where the console is on your host, then restart:

```bash
export MINIO_CONSOLE_PORT=10224
export MINIO_BROWSER_REDIRECT_URL=http://localhost:10224
docker compose -f docker/minio/docker-compose.yml up -d
```

Or use the **default ports 9000 and 9001** so no redirect fix is needed.

## Django

Set in `.env`:

```env
MINIO_ENABLED=true
MINIO_ENDPOINT=localhost:9000
MINIO_ENDPOINT_URL=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=django-media
MINIO_STATIC_BUCKET_NAME=django-static
```

Create buckets `django-media` and `django-static` in the MinIO console if needed.
