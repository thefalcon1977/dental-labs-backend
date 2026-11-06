# GET /camunda/tickets/download — Complexity & Performance Analysis

## Summary

The endpoint streams tickets as NDJSON using the same filters/permissions as the list API, with a cap of 50,000 tickets and a batch size of 100.

---

## Big O Overview

| Dimension | Complexity | Notes |
|-----------|------------|--------|
| **Time (DB round-trips)** | **O(N)** | N = tickets; ~(5 + D) queries per batch of B=100; D = distinct deployments per batch |
| **Time (CPU)** | **O(N × T̄)** | T̄ = average tasks per ticket; building + JSON per ticket |
| **Space (per batch)** | **O(B + T + F)** | B=100, T = tasks in batch, F = form content for batch |
| **Space (stream)** | **O(1)** | Output streamed; no full result buffering |

- **N** = number of tickets (≤ 50,000)
- **B** = batch size (100)
- **D** = distinct deployment IDs in a batch (typically 1–20)
- **T** = total task rows in a batch
- **F** = form content size for the batch

---

## Per-Batch Query Pattern

For each batch of up to 100 ticket IDs:

| Step | DAL call | Queries | Notes |
|------|----------|--------|--------|
| 1 | `fetch_ticket_ids` | 1 | Paginated IDs from `camunda_ticket_ids` |
| 2 | `fetch_ticket_details` | 1 | Details for batch IDs |
| 3 | `fetch_tasks_for_proc_insts` | 1 | All task history for batch |
| 4 | `fetch_proc_inst_deployment_map` | 1 | proc_inst_id → deployment_id |
| 5 | `fetch_ticket_form_keys(db, dep_id)` | **D** | **One call per distinct deployment** |
| 6 | `fetch_ticket_form_data` | 1 | Form content for all keys in batch |

**Total per batch: 5 + D round-trips.**
Number of batches: ⌈N / B⌉ ⇒ **total round-trips O(N)** (with constant factor ~(5+D)/B).

---

## Weaknesses & Solutions

### 1. N+1-style form-keys loading (high impact)

**Issue:** Form keys are loaded with one DB call per distinct deployment in the batch (`for dep_id in deployment_ids: await fetch_ticket_form_keys(db, dep_id)`). With many process definitions, D can be large (e.g. 20–50) and all calls are **sequential**, so latency adds up.

**Solution:** Load form keys for all deployments in the batch in one parallel wave:

```python
# Replace the loop with:
key_results = await asyncio.gather(
    *[fetch_ticket_form_keys(db, dep_id) for dep_id in deployment_ids]
)
form_key_by_deployment_activity = {}
for dep_id, key_rows in zip(deployment_ids, key_results):
    for row in key_rows:
        activity_id = row.get("activity_id")
        form_key = row.get("form_key")
        if activity_id and form_key:
            form_key_by_deployment_activity[(dep_id, activity_id)] = form_key
```

**Effect:** Same number of queries (D) but **parallel** ⇒ wall-clock for this phase drops from O(D) sequential to O(1) (one wave). Total batch time dominated by the slowest of the D calls instead of their sum.

---

### 2. No parallelization of independent batch queries (medium impact)

**Issue:** The first four data loads (IDs already done; then details, tasks, deployment_map) are independent but executed one after another. Same for “form keys wave” vs “form data”: they are sequential.

**Solution:** Run independent queries in parallel with `asyncio.gather`:

```python
# After fetching ids for the batch:
details, tasks, deployment_map = await asyncio.gather(
    fetch_ticket_details(db, ids),
    fetch_tasks_for_proc_insts(db, ids),
    fetch_proc_inst_deployment_map(db, ids),
)
# Then form keys (parallel per deployment, as above), then form data.
```

**Effect:** First wave becomes 1 round-trip instead of 3. Combined with parallel form-keys, total batch time drops from roughly **3 + D + 1** round-trip times to about **1 + 1 + 1** (three waves: details+tasks+deployment, form keys, form data).

---

### 3. Long-held DB session (medium impact)

**Issue:** The same `AsyncSession` is used for the whole stream. For a full 50k-ticket download (500 batches), the session and connection are held for the entire duration. Slow clients or large N increase connection hold time and can exhaust the pool under concurrency.

**Solution:**

- **Option A:** Keep current design but enforce a **read-only, short-lived** session and document that downloads are best run with limited concurrency and/or a dedicated pool.
- **Option B:** Process in a **background task** (e.g. Celery/worker), write NDJSON to object storage (S3/MinIO), return a **download URL** with expiry. Client polls or gets a webhook. Session is only held during the worker run, not during client download.
- **Option C:** Use a **cursor/keyset** and smaller batches so that each HTTP request does a bounded amount of work and returns a “next page” link; client iterates. Session per request is short.

---

### 4. Memory spike per batch (medium impact)

**Issue:** For each batch we hold in memory: all task rows for the batch (can be large if many tasks per ticket), all form key metadata, and **full form content** for every distinct form key. So space is O(B + T + F). With 100 tickets × 30 tasks and 50 KB form content per key, one batch can be in the 5–10 MB range per batch.

**Solution:**

- **Short term:** Keep B=100; ensure form content is loaded only for keys actually used and not duplicated. Current design already deduplicates by form_key.
- **If needed:** Reduce `DOWNLOAD_BATCH_SIZE` (e.g. 50) to lower peak memory at the cost of more batches and round-trips.
- **Optional:** Stream or chunk form content per key instead of loading all into one dict (only if form_content is huge and profiling shows this as a bottleneck).

---

### 5. No client-disconnect handling (low–medium impact)

**Issue:** If the client closes the connection (e.g. user cancels download), the server may still continue the loop and run all batches, wasting DB and CPU.

**Solution:** In FastAPI/Starlette, the generator runs in a request context; when the client disconnects, the task may be cancelled. To be explicit:

- Rely on **request disconnect** propagation (ASGI `receive()` returning a disconnect event) so the generator is cancelled when the client goes away.
- Optionally, **check** `request.is_disconnected()` (or equivalent) at the start of each batch and break out of the loop if True (requires passing `Request` into the generator or service). Not all ASGI servers support this; document behavior.

---

### 6. JSON serialization (low impact)

**Issue:** `json.dumps(..., ensure_ascii=False)` is called for every ticket. For 50k tickets this is 50k serializations; cost is O(N × payload_size). Usually acceptable.

**Solution:** Only if profiling shows JSON as hot: consider **orjson** for encoding (faster, same NDJSON shape) or pre-building bytes in a buffer and yielding larger chunks to reduce Python overhead. Default is fine unless you see CPU-bound bottlenecks.

---

## Recommended Implementation Order

1. **Parallelize form-keys** (asyncio.gather over deployments) — small code change, clear win.
2. **Parallelize details + tasks + deployment_map** (single asyncio.gather) — small change, fewer round-trip waves.
3. **Document** session hold time and recommend background/job-based download for very large exports.
4. Add **timeout** and **max limit** (50k) in docs; consider **rate limiting** or queue for download endpoint.
5. Optionally **check client disconnect** at batch boundaries if your stack supports it.

---

## Summary Table

| Weakness | Severity | Fix complexity | Suggested action |
|----------|----------|----------------|------------------|
| Sequential form-keys (D calls) | High | Low | Parallelize with asyncio.gather |
| Sequential details/tasks/deployment | Medium | Low | Single asyncio.gather for the three |
| Long-held DB session | Medium | Medium | Document; consider background job for large N |
| Memory per batch (T, F) | Medium | Low | Keep B=100; reduce if needed |
| No disconnect handling | Low–Medium | Low | Rely on ASGI cancel; optional request check |
| JSON encoding | Low | Low | Keep json; consider orjson if CPU-bound |

Overall, **time complexity is O(N)** in tickets and in round-trips, which is expected for “stream all matching tickets.” The main gains are from **reducing round-trip waves per batch** (parallelizing independent queries and form-keys) and from **operational measures** (session hold, background jobs, limits).
