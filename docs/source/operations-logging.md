# Operations: Logging and Troubleshooting

This document is for operations teams running the service in production. It explains how logs are structured, how to trace requests, and how to find the cause of issues quickly.

## Production Log Format

In production (when `APP_DEBUG` is not set or is `false`), the application emits **one JSON object per log line** to stdout. This format is suitable for:

- **Elasticsearch** (or any JSON log aggregator)
- **Grep / jq** for ad-hoc search
- **Structured queries** by field (e.g. `request_id`, `status_code`, `level`)

Example log line:

```json
{"event": "Request completed", "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "method": "GET", "path": "/v1/items/123", "client_host": "10.0.0.5", "status_code": 200, "level": "info", "timestamp": "2025-02-02T12:00:00.123456Z", "logger": "apps.core.middleware.logging"}
```

## Key Fields for Troubleshooting

| Field | Description | Use |
|-------|-------------|-----|
| `request_id` | Unique ID for the HTTP request (UUID). | **Primary key for tracing**: all logs for one request share this ID. |
| `method` | HTTP method (GET, POST, etc.). | Filter by operation type. |
| `path` | Request path (e.g. `/v1/items/123`). | Identify which endpoint was hit. |
| `status_code` | HTTP response status. | Find errors (4xx, 5xx) or success (2xx). |
| `level` | Log level: `info`, `warning`, `error`, `exception`. | Filter by severity. |
| `timestamp` | ISO 8601 timestamp. | Order events and correlate with other systems. |
| `logger` | Logger name (module path). | Locate which part of the app emitted the log. |
| `error`, `error_type` | Present on failures. | Understand exception type and message. |

Domain-specific fields (e.g. `user_id`, `order_id`) may appear when the application logs business events; use them to narrow down which entity was involved.

## Tracing a Request End-to-End

When a user or client reports an error, ask them for the **request ID** if possible. The API exposes it in two ways:

1. **Response header**
   Every response includes `X-Request-ID`. The client can read this from the response headers.

2. **Error response body**
   For error responses (4xx, 5xx), the JSON body includes `error.details.request_id` when a request ID is available. Example:

   ```json
   {
     "error": {
       "message": "Resource not found",
       "type": "NotFoundError",
       "details": {
         "resource": "Item",
         "identifier": "123",
         "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
       }
     }
   }
   ```

**How to trace in logs:**

1. Get the `request_id` from the client (header or error body).
2. Search logs for that ID (e.g. in Elasticsearch: `request_id:"a1b2c3d4-e5f6-7890-abcd-ef1234567890"`, or with grep on stdout: `docker compose logs app | grep "a1b2c3d4-e5f6-7890-abcd-ef1234567890"`).
3. All log lines with that `request_id` belong to the same request: start, completion, and any errors in between.

This lets you see the full lifecycle of the request and where it failed.

## What Is *Not* Logged (Security)

The application does **not** log:

- **Authorization headers** or tokens
- **Cookies** or session identifiers
- **Full request/response bodies** for sensitive endpoints
- **PII** beyond what is necessary (prefer stable IDs like `user_id`)

If you need to debug auth or payload issues, use non-production environments and redact before sharing.

## Quick Checks for Common Issues

| Symptom | Where to look | What to search |
|---------|----------------|----------------|
| High 5xx rate | Error logs, metrics | `level: "error"` or `status_code: 500` |
| Slow requests | Request completion logs | `event: "Request completed"` and high `X-Process-Time` (if present) or duration in metrics |
| Failed auth | Application logs | `status_code: 401`, `UnauthorizedError` |
| Database issues | Application + SQLAlchemy logs | `DatabaseError`, `SQLAlchemyError`, pool/connection messages |
| Specific user/entity | Domain fields | `user_id`, `order_id`, or similar fields in log events |

## Correlation with Downstream Services

Outbound HTTP calls (e.g. to Keycloak or other APIs) send the current request ID in the `X-Request-ID` header. If those services log that header, you can correlate logs across systems using the same ID.

## Configuration Affecting Logs

Relevant settings (see Configuration Reference for full list):

- **`APP_LOG_LEVEL`**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Production should typically be `INFO` or `WARNING`.
- **`APP_DEBUG`**: When `true`, logs are pretty-printed (non-JSON) and may include more detail. Keep `false` in production for JSON and security.

## Summary

- **Request ID** is the main key for tracing: get it from `X-Request-ID` or `error.details.request_id` and search logs by it.
- **Production logs are JSON**; use `request_id`, `method`, `path`, `status_code`, and `level` to find and diagnose issues.
- **Error responses** include `request_id` when available so clients can report it to ops.
- **Do not log secrets or PII**; use stable identifiers and follow the project’s logging and observability rules.

For more on what to log and metrics, see `.cursor/rules/observability.mdc` and `.cursor/rules/fastapi-logging.mdc`.
