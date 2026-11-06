# Advance Search Implementation Documentation

## Overview
This document provides a comprehensive business-level guide for the advance-search endpoint. It covers all logic, filters, criteria (AND/OR), sorting, pagination, column selection, and data assembly requirements without any code implementation details.

The endpoint is implemented using **historical tables only**. All process instances (active, completed, cancelled, suspended, and externally terminated) are read from the Process Instance History table and related history tables. Runtime tables are not used. The **whole implementation is in SQL**: three PostgreSQL functions provide the base—IDs (filter + sort + paginate), Count (same filters, total count), and Details (enrich by IDs). Advance-search supports simple filters, nested logical criteria, and flexible column projection.

---

## 1. BASE QUERY STRUCTURE (SQL FUNCTIONS)

The advance-search implementation is built on **three SQL functions**. This split keeps filtering/sorting/pagination in one place (IDs), total count in another (Count), and row enrichment in a third (Details), so the API can call them in sequence and assemble the response.

### 1.1 Data Source (History Only)
All three functions read only from history (and definition/title) tables:

**Physical tables (Camunda-style names):**
- **act_hi_procinst** – Process instance history (proc_inst_id_, business_key_, proc_def_id_, start_time_, end_time_, start_user_id_, state_, delete_reason_, duration_)
- **act_re_procdef** – Process definition (id_, name_)
- **act_ru_execution_titles** – Execution titles (execution_id_, instance_title_) for instance title when present
- **act_hi_taskinst** – Task history (proc_inst_id_, id_, assignee_, end_time_, delete_reason_, name_)
- **act_hi_identitylink** – Identity links (task_id_, user_id_, group_id_, type_)
- **act_hi_actinst** – Activity instance history (proc_inst_id_, act_name_, end_time_)
- **act_id_membership** – User–group membership (user_id_, group_id_) for “same group as creator” rule

Logical equivalents: ProcessInstanceHistory = act_hi_procinst, ProcessDefinition = act_re_procdef, RuntimeExecutionTitle = act_ru_execution_titles, TaskHistory = act_hi_taskinst, IdentityLinkHistory = act_hi_identitylink, ActivityInstanceHistory = act_hi_actinst.

### 1.2 Three-Function Strategy

**1) `camunda_ticket_ids(...)`**
- **Purpose:** Return the list of process instance IDs that match the filters, in the requested sort order, with LIMIT/OFFSET applied.
- **Inputs:** All filter parameters (ticket_type, ticket_number, ticket_title, ticket_status, creator_list, processor_list, assignee_list, phase_list, start_time_from/to, end_time_from/to, pending_basket_ids, processed_by_basket_ids, user_basket_ids), plus sort_by, sort_order, limit_count, offset_count.
- **Output:** A table with one column: `proc_inst_id_` (text). One row per matching process instance in sort order, after OFFSET/LIMIT.
- **Logic:** Single SELECT from act_hi_procinst (and joins/CTEs) with WHERE built from parameters, ORDER BY from sort_by/sort_order, LIMIT/OFFSET. Uses CTEs (e.g. processor_agg) for sort keys; uses EXISTS for processor, assignee, phase, pending, processed_by, and user_basket filters.

**2) `camunda_ticket_details(proc_inst_ids text[])`**
- **Purpose:** Return full ticket rows for the given process instance IDs (e.g. the page of IDs from `camunda_ticket_ids`).
- **Inputs:** `proc_inst_ids` – array of process instance IDs.
- **Output:** A table with columns: ticket_uid, ticket_title, ticket_number, ticket_type, ticket_status, current_phases, current_processors, creator, duration, create_time, end_time. One row per ID in the input array; status and duration derived in SQL (CASE expressions).
- **Logic:** SELECT from act_hi_procinst joined to act_re_procdef and act_ru_execution_titles, plus CTEs for phase_agg and processor_agg (from act_hi_taskinst and act_hi_identitylink for active tasks only). WHERE ahp.proc_inst_id_ = ANY(proc_inst_ids). No filter/sort/pagination—only enrichment by ID list.

**3) `camunda_ticket_count(...)`**
- **Purpose:** Return the total number of process instances that match the **same** filter parameters as `camunda_ticket_ids`, with no sort or pagination.
- **Inputs:** Same filter parameters as `camunda_ticket_ids` (ticket_type, ticket_number, ticket_title, ticket_status, creator_list, processor_list, assignee_list, phase_list, start_time_from/to, end_time_from/to, pending_basket_ids, processed_by_basket_ids, user_basket_ids). No sort_by, sort_order, limit_count, offset_count.
- **Output:** A single bigint: COUNT(*).
- **Logic:** Same WHERE conditions as the IDs query (expressed as EXISTS/subqueries on act_hi_procinst), without ORDER BY / LIMIT / OFFSET. Ensures total_count and has_more are consistent with the IDs result set.

### 1.3 API Execution Flow
1. Validate request (limit, offset, date ranges, criteria if present, etc.).
2. Map API request to function parameters (see **Request structure** below).
3. Call **camunda_ticket_count**(...) → total_count.
4. Call **camunda_ticket_ids**(...) → page of proc_inst_id_ values.
5. If the page is non-empty, call **camunda_ticket_details**(array of those IDs) → ticket rows.
6. Map details columns to API ticket shape (ticket_uid → ticket_id, current_phases → ticket_phases array, etc.); add envelope (total_count, limit, offset, has_more, query_time_ms, search_metadata).

### 1.4 Query Construction Strategy (Within the Functions)
- All filtering is done in SQL in `camunda_ticket_ids` and `camunda_ticket_count` via WHERE and EXISTS.
- Sorting and pagination are applied only in `camunda_ticket_ids` (ORDER BY + LIMIT/OFFSET).
- Enrichment (phases, processors, status, duration) is done in `camunda_ticket_details` so only the current page is enriched.

### 1.3 Required Joins

**For History Query:**
- Join ProcessInstanceHistory with ProcessDefinition (proc_def_id_)
- Outer join RuntimeExecutionTitle (execution_id_ = proc_inst_id_, and end_time_ IS NULL) for active instances’ titles
- Outer join HistoryProcessInstanceTitle (proc_inst_id_, and end_time_ IS NOT NULL) for completed instances’ titles
- Subquery with ActivityInstanceHistory for progress_percent
- Optional joins for criteria: VariableHistory, VariableDetailHistory, ActivityInstanceHistory, TaskHistory, IdentityLinkHistory, form fields as needed by field handlers

### 1.4 Data Selection
Select the following from the history query:

- Process instance ID (proc_inst_id_)
- Business key (ticket number)
- Process definition name (ticket type)
- Start user ID (creator)
- Instance title (from HistoryProcessInstanceTitle or RuntimeExecutionTitle via COALESCE)
- Start time (create_time)
- End time (nullable)
- Process duration (computed from start_time and end_time)
- Progress percent (scalar subquery over ActivityInstanceHistory)
- Ticket status (CASE expression from end_time_, delete_reason_: ACTIVE, SUSPENDED, COMPLETED, CANCELLED, EXTERNALLY_TERMINATED)
- Tenant ID (from history)
- Delete reason (for status derivation)

---

## 2. FILTERS

### 2.1 Filter Application Rules
- Filters are applied at SQL level using WHERE clauses or expressions built by field handlers
- When **criteria** is provided, it becomes the primary filter; simple top-level filter fields may be merged into the same criteria tree or applied in addition (implementation merges basic + advance criteria into one condition per query)
- Multiple simple filters are combined with AND logic
- Array/list filters (e.g. creator, ticket_status) use OR logic within the filter (any match)
- Text filters use ILIKE for case-insensitive partial match where appropriate
- All filters are applied to the single history query; field handlers reference only history tables (ProcessInstanceHistory, VariableHistory, ActivityInstanceHistory, TaskHistory, IdentityLinkHistory, etc.)

### 2.2 Simple (Top-Level) Filters

**Ticket Number (ticket_number)**
- Filter by business key
- Partial match (contains) with ILIKE pattern: `%{ticket_number}%`
- Applied to ProcessInstanceHistory.business_key_

**Ticket Type (ticket_type)**
- Filter by process definition name
- Applied to ProcessDefinition.name_

**Ticket Title (ticket_title)**
- Filter by instance title
- Uses partial match (ILIKE) against instance title from HistoryProcessInstanceTitle or RuntimeExecutionTitle (COALESCE), as joined to ProcessInstanceHistory

**Creator (creator)**
- Filter by start user (process instance creator)
- Accepts comma-separated list of user IDs (OR logic)
- Applied to ProcessInstanceHistory.start_user_id_
- Uses IN clause for multiple values

**Current Processor (current_processor)**
- Filter by current assignee or candidate users/groups on **active** tasks
- Accepts comma-separated list of users/groups (OR logic)
- Resolved via TaskHistory (assignee_) and IdentityLinkHistory (user_id_, group_id_, type_ = candidate) for tasks where end_time_ IS NULL
- Only process instances that have at least one such active task matching the processor list are returned; completed instances (no active tasks) do not match

**Ticket Phases (ticket_phases)**
- Filter by current activity names (phases)
- List of phase names; ticket matches if it has at least one of these phases currently active
- Uses ActivityInstanceHistory where end_time_ IS NULL for the activity instance (act_name_ IN phases)
- OR logic: any phase match includes the ticket

### 2.3 Time Range Filters

**Create Time From (create_time_from)**
- Filter tickets created on or after this date/time
- Supports partial ISO 8601: date only, date+hour, date+hour+minute, full datetime
- Applied to ProcessInstanceHistory.start_time_
- Truncation may be applied to column for day/hour boundaries when partial value is sent

**Create Time To (create_time_to)**
- Filter tickets created on or before this date/time
- Same format and truncation as create_time_from
- Validation: create_time_to must be >= create_time_from when both provided

**End Time From (end_time_from)**
- Filter tickets ended on or after this date/time
- Applied to ProcessInstanceHistory.end_time_

**End Time To (end_time_to)**
- Filter tickets ended on or before this date/time
- Validation: end_time_to must be >= end_time_from when both provided

**End Time To Exclusive (end_time_to_exclusive)**
- Internal/optional; applied to ProcessInstanceHistory.end_time_ when supported

### 2.4 Status Filter (ticket_status)

**Status Values:**
- ACTIVE: Process is still running (end_time_ IS NULL in history)
- COMPLETED: Process finished normally (end_time set, delete_reason NULL or empty)
- CANCELLED: Process was cancelled (delete_reason contains "cancelled" or "canceled")
- SUSPENDED: Process is suspended (derived from history if suspension state is stored there)
- EXTERNALLY_TERMINATED: Process was terminated (delete_reason contains "terminated"/"termination")

**Filter Behavior:**
- Accepts comma-separated list of statuses (OR logic)
- Status is derived per row from history via CASE on end_time_ and delete_reason_ (see Status Derivation in section 12)

### 2.5 Tenant Filter (tenant_id)
- Filter by tenant ID for multi-tenancy
- Applied to ProcessInstanceHistory.tenant_id_

### 2.6 Advanced Criteria (criteria)

When **criteria** is present and valid, it defines a nested logical expression over conditions. Simple filters may still be normalized into this tree so that a single combined condition is applied per query.

**Root Structure:**
- Must have either:
  - `"operator": "and" | "or"` and `"conditions": [ ... ]`, or
  - A group-like structure with `"type": "group"` and `"children": [ ... ]`

**Condition Types:**
- **Leaf condition:** `{ "field": "<field_name>", "action": "<operator>", "value": <value> }`
- **Nested group:** `{ "operator": "and"|"or", "conditions": [ ... ] }` (recursive)

**How AND and OR Work Together:**
- An **"and"** node is true when **all** of its children (conditions or nested groups) evaluate to true.
- An **"or"** node is true when **at least one** of its children evaluates to true.
- Evaluation is recursive: inner groups are evaluated first, then the result is used as a single boolean for the parent.
- The entire tree is converted into one SQL boolean expression and applied as a single filter to the query.

**Example:**
```json
{
  "operator": "and",
  "conditions": [
    { "field": "creator", "action": "==", "value": "john.doe" },
    {
      "operator": "or",
      "conditions": [
        { "field": "ticket_status", "action": "in", "value": ["COMPLETED", "CANCELLED"] },
        { "field": "end_time", "action": "is_empty" }
      ]
    }
  ]
}
```
Meaning: creator is john.doe AND (ticket_status in {COMPLETED, CANCELLED} OR end_time is empty).

**Supported Fields in Criteria:**
- ticket_number, ticket_type, ticket_title, ticket_status
- creator, create_time, end_time
- duration_ms, process_duration
- current_processors (alias: processor, current_processor)
- ticket_phases, tenant_id
- variable (requires variable_name), form_field (requires form_field_key)
- assignee, creator_main_group, sub_ticket, associated

**Supported Actions:**
- Comparison: ==, !=, >, <, >=, <=
- Text: like, ilike, not_like, not_ilike
- Set: in, not_in
- Emptiness: is_empty, is_not_empty

**Field-Specific Rules:**
- sub_ticket, associated: only is_empty, is_not_empty
- duration_ms, process_duration: no text actions (like/ilike)
- variable: must include variable_name in the condition
- form_field: must include form_field_key (and optionally activity)

### 2.7 Form Field Criteria (Legacy)
- If **form_field_criteria** is provided and no other criteria exist, it is converted into a synthetic criteria condition using the form_field field handler
- Structure: form_field_key, action, value, optional activity

### 2.8 Prefiltered IDs
- For some criteria (e.g. form fields, variables), the service may first resolve a set of process instance IDs that match, then inject that set into the main query (IN clause)
- If the prefilter returns no IDs (from history tables), the main history query returns no rows

---

## 3. SORTING

### 3.1 Sort Parameters
- **sort_by:** Field to sort by (default: "create_time")
- **sort_order:** "asc" or "desc" (default: "desc")

### 3.2 Supported Sort Fields

**create_time**
- Process instance start time (ProcessInstanceHistory.start_time_)

**end_time**
- Process instance end time (ProcessInstanceHistory.end_time_)
- NULLs last

**ticket_number**
- Business key (business_key_)

**ticket_type**
- Process definition name (ProcessDefinition.name_)

**creator**
- Start user ID (ProcessInstanceHistory.start_user_id_)

**ticket_status**
- Derived status; may require expression or post-processing

**duration_ms / process_duration**
- Computed duration from start_time and end_time

**current_processors**
- Current assignees/candidates; may require subquery over TaskHistory/IdentityLinkHistory or post-sort

**ticket_phases**
- Current phase names; may require subquery over ActivityInstanceHistory or post-sort

### 3.3 Sorting Implementation Strategy
- Sorting is applied at SQL level on the history query (ORDER BY on history columns or computed expressions).
- Complex sorts (e.g. current_processors, ticket_phases) may be applied in SQL via subqueries or in Python after fetch; implementation uses SQL where possible for pagination correctness.
- NULL values are handled consistently (e.g. NULLS LAST).
- Secondary sort by process instance ID ensures stable ordering.

### 3.4 Sort Order Handling
- Default sort_order is "desc"
- Case-insensitive ("asc", "desc", "ASC", "DESC")

---

## 4. PAGINATION

### 4.1 Pagination Parameters
- **limit:** Number of items per page (default: 50, min: 1, max: 200)
- **offset:** Number of items to skip (default: 0, min: 0)

### 4.2 Pagination Strategy
- Total count is the count of distinct process instances from the history query (after all filters).
- Main result set is produced by the same history query with ORDER BY, LIMIT, and OFFSET applied at the database level.

### 4.3 Total Count Calculation
- Total count is the count of distinct process instance IDs from the filtered history query (e.g. COUNT(*) from a subquery or equivalent).

### 4.4 Has More Flag
- **has_more = (offset + limit) < total_count**
- Returned in response metadata.

### 4.5 Performance
- LIMIT/OFFSET applied in SQL on the history query to avoid loading full result set into memory.
- Large offsets may still be costly; consider cursor-based pagination for very large datasets if needed later.

---

## 5. COLUMN SELECTION (PROJECTION)

### 5.1 Purpose
- **selected_columns** controls which fields appear in each ticket in the response.
- It does **not** affect which tickets match the filters (filtering is determined by simple filters and criteria).

### 5.2 Basic Columns
- ticket_id (always included), ticket_number, ticket_type, ticket_title, ticket_status
- create_time, end_time, creator
- current_processors, ticket_phases
- duration_ms, process_duration, tenant_id
- operation_time, operator
- activities (when requested, triggers activity/variable enrichment)

### 5.3 Variable and Activity Columns
- **variables** – all variables; **variables.{name}** – specific variable
- **variable.{name}** – single variable
- **activity__{activityKey}.{field}** – activity-scoped field
- **activity__{activityKey}.variables.{varName}** – activity-scoped variable
- **activities.summary**, **activities.active**, **activities.completed** – activity aggregates

### 5.4 Conditional Columns
- **if_active:field** – include field only when ticket is active
- **if_completed:field** – include field only when ticket is completed

### 5.5 Computed Columns
- **age_hours** – hours since creation
- **progress_percent** – completion percentage (from activity counts)

### 5.6 Null Handling
- Fields not requested or not applicable may be omitted from the ticket object (exclude_none behavior).
- List fields may be returned as empty arrays when applicable.

---

## 7. DATA ASSEMBLY

### 7.1 Ticket Data Structure

**Core Fields:**
- ticket_id: Process instance ID
- ticket_number: Business key
- ticket_type: Process definition name
- ticket_status: ACTIVE | COMPLETED | CANCELLED | SUSPENDED | EXTERNALLY_TERMINATED (derived from history end_time_, delete_reason_)
- ticket_title: Instance title from HistoryProcessInstanceTitle or RuntimeExecutionTitle (COALESCE), as joined to history
- creator: Start user ID
- create_time: Start time (ISO 8601)
- end_time: End time (ISO 8601, nullable)
- duration_ms / process_duration: Computed duration (nullable)

**Assignment and Phase:**
- current_processors: List of current assignees/candidates (from active tasks in TaskHistory/IdentityLinkHistory; empty for completed instances)
- ticket_phases: List of active activity names (from ActivityInstanceHistory where end_time_ IS NULL)

**Metadata:**
- tenant_id, operation_time, operator (when requested)

**Enriched (when requested via selected_columns):**
- activities: List of activity objects with id, name, type, assignee, state, start_time, end_time, duration, variables

### 7.2 Data Enrichment Process
- Base row comes from the history query result.
- **ticket_status** is taken from SQL CASE or derived from end_time_ and delete_reason_ (see Status Derivation in section 12).
- **process_duration** / **progress_percent** come from SQL-computed columns on the history query.
- **current_processors** and **ticket_phases**: loaded when needed (e.g. for selected_columns or default set), via TaskHistory, IdentityLinkHistory, and ActivityInstanceHistory (active tasks/activities only).
- **operation_time** / **operator**: derived from latest completed user task or form completion (from history).
- **activities** and **variables**: loaded only when requested in selected_columns; may require additional queries per ticket or batch, using history tables.

### 7.3 Field Logic (History Tables Only)

This section extracts the field-level logic used by the advance-search endpoint, limited to history tables only.

**Basic Information (Latest Values)**
- **ticket_id:** Process instance ID from ProcessInstanceHistory (act_hi_procinst.proc_inst_id_/id_).
- **ticket_number:** Business key from ProcessInstanceHistory.business_key_.
- **ticket_type:** Process definition name from ProcessDefinition (act_re_procdef.name_).
- **ticket_title:** Instance title from HistoryProcessInstanceTitle (historical title table, joined by proc_inst_id_).
- **creator:** Start user ID from ProcessInstanceHistory.start_user_id_.
- **create_time:** Start time from ProcessInstanceHistory.start_time_.
- **end_time:** End time from ProcessInstanceHistory.end_time_ (nullable).
- **tenant_id:** Tenant from ProcessInstanceHistory.tenant_id_ (when selected).
- **basic_information.variables.* (process-level):** Latest value per variable name by max(VariableHistory.create_time_) for each proc_inst_id_.

**Start-Event (Create) Variables (Earliest Values)**
- **activity__{StartEventKey}.variables.* (no basic_information suffix):** Earliest value per variable name by min(VariableHistory.create_time_) for variables tied to the start-event activity instance (act_inst_id_ = start-event activity instance ID), with fallback to act_inst_id_ = proc_inst_id_ for start-event cases.
- **start-event form fields:** Earliest value by min(VariableDetailHistory.time_) for VariableUpdate records, joined to the start-event activity instance.
- **activity__{StartEventKey}__basic_information.variables.*:** Uses the process-level **latest** values (same as basic_information), not the earliest start-event values.

**Status and Time**
- **ticket_status:** Derived from history (end_time_, delete_reason_, and state_ where available). See Status Derivation in section 12.
- **duration_ms / process_duration:** If end_time_ is NULL, duration is “now - start_time_”; otherwise use ProcessInstanceHistory.duration_.
- **age_hours:** Computed as hours between now and start_time_ (history only).

**Assignment and Phase**
- **current_processors:** Derived from active tasks in TaskHistory and IdentityLinkHistory (act_hi_taskinst + act_hi_identitylink where end_time_ IS NULL). Assignee and candidate users/groups are combined and deduplicated.
- **ticket_phases:** Derived from active activity instances in ActivityInstanceHistory (act_hi_actinst where end_time_ IS NULL), using act_name_.

**Progress**
- **progress_percent:** Computed from ActivityInstanceHistory by comparing completed vs total activities for the process instance.

**Operation Fields (operation_time / operator)**
- **operation_time:** Computed from ActivityInstanceHistory with these rules:
  - Find the latest activity by start_time.
  - If that activity has end_time → use it.
  - If latest end_time is NULL but a previous activity has end_time → use the most recent non-NULL end_time.
  - If no activities have end_time → use ticket end_time when present.
  - If ticket end_time exists and is later than activity-derived operation_time → use ticket end_time.
- **operator:** Uses the **same activity selection logic as operation_time** to pick the activity, then returns its assignee. If that activity has no assignee, walk backward to the most recent activity with an assignee.

**Activities and Variables**
- **activities.active / activities.completed:** Built from ActivityInstanceHistory (end_time_ IS NULL for active, NOT NULL for completed).
- **activities.summary:** Aggregated counts and timing info from ActivityInstanceHistory per process instance.
- **variables / variables.{name}:** From VariableDetailHistory (act_hi_detail) only, scoped by proc_inst_id_.
- **activity__{activityKey}.* and activity-scoped variables:** From ActivityInstanceHistory joined to VariableDetailHistory by activity instance (latest values for non-start-event activities).

### 7.4 Response Format
- **tickets:** Array of ticket objects (after projection and null exclusion)
- **total_count:** Total matching tickets
- **limit, offset:** Echo of request
- **has_more:** Boolean
- **query_time_ms, db_query_count, db_time_ms, sql_time_ms, python_time_ms:** Performance metrics
- **search_metadata:** Filters applied, criteria complexity, fields_used, actions_used, search_executed_at, etc.

---

## 8. PERFORMANCE CONSIDERATIONS

### 8.1 Query Optimization
- Use a single combined criteria condition on the history query (no duplicate filter logic).
- Apply all filters at SQL level.
- Use EXISTS or IN subqueries for processor, phase, and variable conditions where appropriate.
- Avoid loading full result set; use LIMIT/OFFSET on the history query.

### 8.2 Indexing Requirements
- Process instance ID, business key, start_user_id, start_time_, end_time_, proc_def_id_, tenant_id_ on ProcessInstanceHistory and ProcessDefinition.
- TaskHistory and IdentityLinkHistory: proc_inst_id_, assignee_, task_id_, type_, user_id_, group_id_.
- ActivityInstanceHistory: proc_inst_id_, end_time_, act_name_.
- Variable history tables: proc_inst_id_, name_.

### 8.3 Query Execution Strategy
- Build a single history query with all filters, sorting, and pagination.
- Use parameterized queries and connection pooling.
- Fetch only columns needed for the response and for the requested selected_columns.
- Enrich (activities, variables, processors) only for the paginated subset when possible.

### 8.4 Monitoring and Metrics
- Track query_time_ms, db_time_ms, sql_time_ms, python_time_ms, db_query_count.
- Log slow queries and large result counts.
- search_metadata can expose criteria_complexity and condition count for tuning.

---

## 9. ERROR HANDLING

### 9.1 Input Validation
- **limit:** 1 <= limit <= 200
- **offset:** >= 0
- **ticket_status:** Comma-separated list of valid enum values; invalid values return 400 with message
- **create_time_to >= create_time_from**, **end_time_to >= end_time_from**
- **criteria:** Must have operator and conditions (or type/children); conditions non-empty; each leaf has field and action; value required unless action is is_empty/is_not_empty; variable/form_field have required keys
- **current_processor:** Non-empty after trimming; max number of values enforced
- **creator, ticket_phases:** Similar limits and format checks

### 9.2 Database Error Handling
- On SQLAlchemy/database errors: log, record metrics, return 500 with DATABASE_QUERY_FAILED.
- On query timeout or connection errors: same treatment.

### 9.3 Criteria Validation Errors
- Invalid structure, unknown field, or invalid action: return 400 with INVALID_CRITERIA and list of issues.
- Contradictory criteria (e.g. is_empty AND is_not_empty for same field): return empty result set without error (or short-circuit).
- Tautologies (e.g. is_empty OR is_not_empty): criteria may be simplified or removed.

### 9.4 Authentication
- If authentication is enabled, require valid JWT; return 401 on failure.
- User basket (user_id, groups) can be used for future permission filtering; not required for basic advance-search contract.

---

## 10. IMPLEMENTATION TASKS (SQL-FUNCTION-BASED)

### Task 1: Deploy the Three SQL Functions
1. Create **camunda_ticket_ids**(...) with filter, sort, and pagination parameters; return TABLE(proc_inst_id_ text). Use act_hi_procinst, act_re_procdef, act_ru_execution_titles, act_hi_taskinst, act_hi_identitylink, act_hi_actinst, act_id_membership. Use CTE processor_agg for sort by processor; use EXISTS for processor, assignee, phase, pending, processed_by, user_basket. ORDER BY via CASE on sort_by/sort_order; LIMIT limit_count OFFSET offset_count.
2. Create **camunda_ticket_count**(...) with the same filter parameters (no sort/limit/offset); return bigint. Reuse the same WHERE logic as camunda_ticket_ids.
3. Create **camunda_ticket_details**(proc_inst_ids text[]); return ticket_uid, ticket_title, ticket_number, ticket_type, ticket_status (CASE), current_phases, current_processors, creator, duration (CASE), create_time, end_time. Use CTEs phase_agg and processor_agg; WHERE ahp.proc_inst_id_ = ANY(proc_inst_ids).

### Task 2: API Layer Mapping
1. Map API request body to function parameters (see **Request structure**): ticket_type, ticket_number, creator → creator_list (array), current_processor → processor_list, ticket_phases → phase_list, create_time_from/to → start_time_from/to, end_time_from/to, sort_by, sort_order, limit, offset → limit_count, offset_count. Optional: pending_basket_ids, processed_by_basket_ids, user_basket_ids.
2. Call camunda_ticket_count(...) → total_count.
3. Call camunda_ticket_ids(...) → list of proc_inst_id_.
4. If list non-empty, call camunda_ticket_details(array_of_ids) → ticket rows.
5. Map details output to API ticket object (see **Response structure**): ticket_uid → ticket_id, current_phases → ticket_phases (split), current_processors → current_processors (split), duration → duration_ms/process_duration.
6. Build envelope: total_count, limit, offset, has_more = (offset + limit) < total_count, query_time_ms, db_query_count (e.g. 3), search_metadata.

### Task 3: Validation and Error Handling
1. Validate request (limit 1–200, offset >= 0, date ranges, ticket_status enum, creator/processor/phase list limits).
2. Return 400 for validation errors; 500 for database errors when calling the functions.
3. If criteria (nested AND/OR) is required, either extend the SQL functions to accept a criteria representation or resolve criteria in the application and pass derived simple parameters to the functions.

### Task 4: Performance and Monitoring
1. Measure query_time_ms, db_time_ms (or per-call times for the three functions), db_query_count.
2. Populate search_metadata (filters_applied, search_executed_at).
3. Ensure indexes on act_hi_procinst (id_, proc_def_id_, start_time_, end_time_, start_user_id_, state_), act_hi_taskinst (proc_inst_id_, end_time_, assignee_), act_hi_identitylink (task_id_, type_, user_id_, group_id_), act_hi_actinst (proc_inst_id_, end_time_, act_name_).

---

## 11. SQL FUNCTION DESIGN PATTERNS

The advance-search implementation is **entirely in SQL**. The following design patterns apply to the three PostgreSQL functions (camunda_ticket_ids, camunda_ticket_count, camunda_ticket_details) and keep filtering, counting, sorting, pagination, and enrichment consistent and maintainable.

### 11.1 Three-Function Split (Separation of Concerns)
- **IDs function:** Encapsulates all filter logic, sort logic, and pagination. Returns only process instance IDs. Single responsibility: “which tickets match, in what order, for this page.”
- **Count function:** Reuses the **same** filter logic as the IDs function (same WHERE conditions), with no ORDER BY, LIMIT, or OFFSET. Returns one number. Single responsibility: “how many tickets match.”
- **Details function:** Accepts only a list of IDs; no filter/sort/pagination. Single responsibility: “for these IDs, return full ticket rows (status, phases, processors, duration, etc.).”
- **Benefits:** Count and IDs stay in sync; details is cheap (only current page); each function can be tested and optimized independently; API assembles response by calling the three in sequence.

### 11.2 Parameterization and NULL Semantics
- Every filter (ticket_type, ticket_number, creator_list, processor_list, phase_list, time ranges, basket IDs, user_basket_ids) is a **function parameter**. Default NULL.
- In SQL: “parameter IS NULL” means “do not apply this filter.” Example: `AND (creator_list IS NULL OR ahp.start_user_id_ = ANY(creator_list))`.
- Sort and pagination (sort_by, sort_order, limit_count, offset_count) are parameters only in the IDs function; count has no sort/limit/offset.
- **Benefits:** One SQL definition per function; no string concatenation of filters; safe from injection when parameters are bound; easy to map API request → function arguments.

### 11.3 CTEs for Aggregations and Sort Keys
- **processor_agg:** In the IDs function, a CTE aggregates “first” or “min” processor per proc_inst_id from act_hi_taskinst + act_hi_identitylink (active tasks only). Used in ORDER BY when sort_by = 'processor'.
- **phase_agg, processor_agg:** In the details function, CTEs aggregate current_phases (STRING_AGG of task names) and current_processors (assignee + candidate user_id_ + group_id_, deduplicated, STRING_AGG) per proc_inst_id. Used in the SELECT list.
- **Benefits:** Sort and enrichment logic is readable; no repeated subqueries in ORDER BY or SELECT; planner can optimize CTEs once per function.

### 11.4 EXISTS for Filter Conditions
- Processor, assignee, phase, pending_basket, processed_by_basket, and user_basket filters are expressed with **EXISTS** subqueries (e.g. “EXISTS (SELECT 1 FROM act_hi_taskinst aht ... WHERE aht.proc_inst_id_ = ahp.id_ AND ...)”).
- **Benefits:** Stops at first match; avoids duplicate rows; same pattern in both IDs and count; index-friendly (proc_inst_id_, end_time_, assignee_, etc.).

### 11.5 Status and Duration in SQL (CASE Expressions)
- **ticket_status:** Derived in the details function with a CASE on ahp.end_time_, ahp.state_, and ahp.delete_reason_ (e.g. end_time_ IS NULL → ACTIVE/SUSPENDED by state_; end_time_ IS NOT NULL and delete_reason_ ILIKE '%terminated%' → EXTERNALLY_TERMINATED; etc.).
- **duration:** CASE: when end_time_ IS NULL use EXTRACT(EPOCH FROM (now - start_time_)) * 1000; else use ahp.duration_.
- **Benefits:** No application-side derivation of status or duration; single source of truth in SQL; same logic for every caller.

### 11.6 Deterministic Ordering and Tiebreaker
- ORDER BY is built from sort_by and sort_order (e.g. CASE WHEN sort_by = 'create_time' AND sort_order = 'desc' THEN ahp.start_time_ END DESC, ...). Only one CASE branch is non-NULL per row.
- **Tiebreaker:** Final ORDER BY column is ahp.id_ (or proc_inst_id_) so ordering is deterministic across pages.
- **Benefits:** Stable pagination; no “missing” or “duplicate” rows when moving between pages.

### 11.7 STABLE and Read-Only
- All three functions are declared **STABLE** (and LANGUAGE sql). They do not modify data; they only read from act_hi_*, act_re_*, act_ru_execution_titles, act_id_membership.
- **Benefits:** Planner can optimize and cache; safe for replication and reporting; no locking of rows for update.

### 11.8 Single Source of Truth (History Tables)
- All data comes from **act_hi_procinst** and related history/definition/title tables. No runtime tables. Same table set in IDs, count, and details.
- **Benefits:** Consistent semantics; no UNION; no “which table to query” branching; simpler indexing and tuning.

---

## 12. IMPORTANT NOTES AND TIPS

### 12.1 Criteria vs Simple Filters
- When **criteria** is present, it is the primary filter; simple filters are typically merged into the same condition tree so that one WHERE clause is applied per query.
- Use simple filters for straightforward UIs; use criteria for nested AND/OR and emptiness checks.

### 12.2 History-Only Implementation
- Advance-search is implemented using historical tables only. All process instances (active, completed, cancelled, suspended, externally terminated) are read from Process Instance History and related history tables. No runtime tables are used.
- **Variable search uses act_hi_detail only;** act_hi_varinst (VariableHistory) and act_ru_* (VariableRuntime) are not used for variable filtering or enrichment in advance-search.

### 12.3 Column Selection and Performance
- Request only the columns you need (selected_columns) to reduce data transfer and enrichment work (activities, variables, processors).

### 12.4 Time Handling
- Store and compare times in UTC; support partial ISO 8601 for create_time and end_time ranges.
- Truncate to day/hour/minute when partial values are sent so that ranges match user expectations.

### 12.5 Status Derivation (History)
- **ticket_status** is derived from ProcessInstanceHistory.end_time_ and delete_reason_:
  - end_time_ IS NOT NULL and delete_reason_ contains "cancelled" or "canceled" → CANCELLED
  - end_time_ IS NOT NULL and delete_reason_ contains "terminated" or "termination" → EXTERNALLY_TERMINATED
  - end_time_ IS NOT NULL and (delete_reason_ IS NULL or delete_reason_ = '') → COMPLETED
  - end_time_ IS NOT NULL and delete_reason_ not matched above → EXTERNALLY_TERMINATED
  - end_time_ IS NULL → ACTIVE (SUSPENDED if needed can be derived from suspension state where available in history)

### 12.6 Current Processors
- current_processors are resolved from TaskHistory and IdentityLinkHistory for **active** tasks (end_time_ IS NULL). Completed instances have no active tasks, so current_processors is empty for them. Filtering by current_processor returns only instances that have at least one active task matching the processor list.

### 12.7 Testing
- Test with criteria only, simple filters only, and both.
- Test AND/OR nesting (single level and deep).
- Test all status values (ACTIVE, COMPLETED, CANCELLED, SUSPENDED, EXTERNALLY_TERMINATED) against the history query.
- Test pagination and sort on the history result set.
- Test selected_columns (minimal set vs full/activities/variables).
- Test validation errors (invalid criteria, invalid status, invalid date range).

---

## 13. REQUEST STRUCTURE (API → SQL FUNCTION INPUTS)

The API request body is mapped to the parameters of the SQL functions as follows. This defines how inputs and outputs of the SQL functions align with the advance-search API.

### 13.1 Mapping: API Request → camunda_ticket_ids / camunda_ticket_count

| API request field        | SQL function parameter   | Type (SQL)   | Notes |
|--------------------------|---------------------------|--------------|--------|
| ticket_type              | ticket_type               | text         | NULL = not applied. Process definition name filter (ILIKE). |
| ticket_number            | ticket_number             | text         | NULL = not applied. Business key (ILIKE). |
| ticket_title             | ticket_title              | text         | NULL = not applied. Instance title (ILIKE). |
| ticket_status            | ticket_status             | text         | NULL = not applied. Single value: ACTIVE, SUSPENDED, COMPLETED, CANCELLED, EXTERNALLY_TERMINATED. Matched to ahp.state_ in SQL. |
| creator                  | creator_list              | text[]       | Comma-separated string → array. NULL = not applied. start_user_id_ = ANY(creator_list). |
| current_processor        | processor_list            | text[]       | Comma-separated → array. NULL = not applied. EXISTS on act_hi_taskinst + act_hi_identitylink (active tasks, assignee/candidate). |
| assignee                 | assignee_list             | text[]       | NULL = not applied. Same tables; supports empty string for “no assignee”. |
| ticket_phases            | phase_list                | text[]       | List of activity names. NULL = not applied. EXISTS on act_hi_actinst (end_time_ IS NULL, act_name_ = ANY(phase_list)). |
| create_time_from         | start_time_from           | timestamptz  | NULL = not applied. ahp.start_time_ >= start_time_from. |
| create_time_to           | start_time_to             | timestamptz  | NULL = not applied. ahp.start_time_ <= start_time_to. |
| end_time_from            | end_time_from             | timestamptz  | NULL = not applied. ahp.end_time_ >= end_time_from. |
| end_time_to              | end_time_to               | timestamptz  | NULL = not applied. ahp.end_time_ <= end_time_to. |
| pending_basket_ids       | pending_basket_ids        | text[]       | Optional. Active tasks: assignee or candidate in list. |
| processed_by_basket_ids  | processed_by_basket_ids    | text[]       | Optional. Completed tasks: assignee or identity link in list. |
| user_basket_ids          | user_basket_ids           | text[]       | Optional. Permission filter: creator, current assignee, candidate, historical involvement, same group as creator. |
| sort_by                  | sort_by                   | text         | Used only in camunda_ticket_ids. Default 'create_time'. Values: create_time, end_time, ticket_number, ticket_type, creator, duration, processor, ticket_title. |
| sort_order               | sort_order                | text         | Used only in camunda_ticket_ids. 'asc' or 'desc'. Default 'desc'. |
| limit                    | limit_count               | int          | Used only in camunda_ticket_ids. Default 50, min 1, max 200. |
| offset                   | offset_count              | int          | Used only in camunda_ticket_ids. Default 0. |

- **camunda_ticket_count** receives the same filter parameters as **camunda_ticket_ids** (ticket_type through user_basket_ids) and has no sort_by, sort_order, limit_count, or offset_count.
- **camunda_ticket_ids** receives all of the above; ORDER BY is built from sort_by/sort_order (e.g. CASE WHEN sort_by = 'create_time' AND sort_order = 'desc' THEN ahp.start_time_ END DESC), with tiebreaker ahp.id_; then LIMIT limit_count OFFSET offset_count.

### 13.2 Mapping: camunda_ticket_details input

| Source                    | SQL function parameter | Type (SQL) | Notes |
|---------------------------|-------------------------|------------|--------|
| Result of camunda_ticket_ids (page of IDs) | proc_inst_ids | text[]     | Array of process instance IDs. Passed as single argument. |

- The API calls **camunda_ticket_details**(array_of_ids) where array_of_ids is the set of proc_inst_id_ values returned by **camunda_ticket_ids** for the current page. If **camunda_ticket_ids** returns no rows, the API may skip calling **camunda_ticket_details** and return an empty tickets array.

### 13.3 Criteria and advanced filters

- If the API supports **criteria** (nested AND/OR), the application layer converts criteria into the same logical filter that the SQL functions express (e.g. by building equivalent WHERE conditions or by calling the same functions with parameters derived from the criteria). The three functions above accept **simple** parameters (single ticket_status, array lists, time ranges); complex criteria may require a separate SQL path or pre-filtering so that the final IDs/count/details align with the criteria.

---

## 14. RESPONSE STRUCTURE (SQL FUNCTION OUTPUTS → API)

### 14.1 Success Response
```
{
  "tickets": [
    {
      "ticket_id": "string",
      "ticket_number": "string|null",
      "ticket_type": "string|null",
      "ticket_title": "string|null",
      "ticket_status": "ACTIVE|COMPLETED|CANCELLED|SUSPENDED|EXTERNALLY_TERMINATED",
      "create_time": "ISO8601|null",
      "end_time": "ISO8601|null",
      "creator": "string|null",
      "current_processors": ["string"]|null,
      "ticket_phases": ["string"]|null,
      "duration_ms": "number|null",
      "process_duration": "number|null",
      "operation_time": "ISO8601|null",
      "tenant_id": "string|null",
      "activities": [ { "id", "name", "type", "assignee", "state", "start_time", "end_time", "duration", "variables" } ]|null
    }
  ],
  "total_count": "number",
  "limit": "number",
  "offset": "number",
  "has_more": "boolean",
  "query_time_ms": "number",
  "db_query_count": "number|null",
  "db_time_ms": "number|null",
  "sql_time_ms": "number|null",
  "python_time_ms": "number|null",
  "search_metadata": {
    "filters_applied": ["string"] | "criteria_complexity", "conditions_count", "fields_used", "actions_used",
    "search_executed_at": "ISO8601"
  }
}
```

### 14.2 Mapping: camunda_ticket_details output → API ticket object

| SQL output column (camunda_ticket_details) | API response field | Notes |
|-------------------------------------------|---------------------|--------|
| ticket_uid                                 | ticket_id           | Process instance ID. |
| ticket_title                               | ticket_title        | Instance title. |
| ticket_number                              | ticket_number       | Business key. |
| ticket_type                                | ticket_type         | Process definition name. |
| ticket_status                              | ticket_status       | ACTIVE \| COMPLETED \| CANCELLED \| SUSPENDED \| EXTERNALLY_TERMINATED. |
| current_phases                             | ticket_phases       | Comma-separated string → split to array of phase names. |
| current_processors                         | current_processors  | Comma-separated string → split to array of processor IDs/names. |
| creator                                    | creator             | start_user_id_. |
| duration                                   | duration_ms / process_duration | Milliseconds (running: computed from start to now; completed: ahp.duration_). |
| create_time                                | create_time         | start_time_. |
| end_time                                   | end_time            | end_time_. |

- The API envelope (total_count, limit, offset, has_more, query_time_ms, db_query_count, db_time_ms, search_metadata) is built from: total_count = result of **camunda_ticket_count**; limit/offset = request values; has_more = (offset + limit) < total_count; timings from application.

### 14.3 Error Response
```
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "issues": [ "optional list for criteria validation" ]
  }
}
```

**Error Codes:**
- INVALID_SEARCH_PARAMETERS: Validation error (e.g. date range, empty current_processor)
- INVALID_CRITERIA: Criteria structure or content invalid (with issues array)
- DATABASE_QUERY_FAILED: Database error
- INTERNAL_SERVER_ERROR: Unexpected error

**HTTP Status Codes:**
- 200: Success
- 400: Validation or invalid criteria
- 500: Database or internal error

---

## 15. SUMMARY

This documentation provides a complete business-level guide for the advance-search endpoint. Key points:

1. **History only:** Advance-search is implemented using **historical tables only** (act_hi_procinst, act_hi_taskinst, act_hi_identitylink, act_hi_actinst, act_re_procdef, act_ru_execution_titles, act_id_membership). Runtime tables are not used; no UNION and no table-selection logic.
2. **Three SQL functions:** The implementation is **entirely in SQL**. **camunda_ticket_ids** returns the page of process instance IDs (filter + sort + pagination). **camunda_ticket_count** returns the total count (same filters, no sort/pagination). **camunda_ticket_details** returns full ticket rows for a given list of IDs. The API calls them in sequence and assembles the response.
3. **Request structure:** API request fields map to function parameters (ticket_type, ticket_number, creator_list, processor_list, phase_list, start_time_from/to, end_time_from/to, sort_by, sort_order, limit_count, offset_count, basket IDs). See **Request structure** for the full mapping.
4. **Response structure:** Ticket rows come from **camunda_ticket_details** output (ticket_uid → ticket_id, current_phases → ticket_phases, etc.); total_count and has_more come from **camunda_ticket_count** and **camunda_ticket_ids**. See **Response structure** for the mapping.
5. **SQL function design patterns:** Three-function split (IDs / Count / Details), parameterization with NULL = “do not apply filter,” CTEs for aggregations and sort keys, EXISTS for filter conditions, CASE for status and duration, deterministic ORDER BY with tiebreaker, STABLE read-only functions.
6. **Filters:** All filters are applied in SQL in camunda_ticket_ids and camunda_ticket_count (text filters ILIKE, array filters = ANY(...), time ranges, processor/assignee/phase/basket EXISTS subqueries, user_basket permission rules).
7. **Validation and errors:** Validate limit, offset, dates, and list sizes in the API layer; return 400/500 and clear error codes.

Follow this documentation to implement or integrate with the advance-search endpoint consistently and correctly.

---

## APPENDIX A: SQL FUNCTION LOCATIONS (NO SQL IN THIS DOC)

This documentation is intentionally **SQL-free** (business/behavior only). The runnable SQL definitions live in the repository under:

- `tasks/tickets/sql/camunda_advance_search_ticket_ids.sql` – filtering + criteria evaluation + sorting + pagination (returns process instance IDs)
- `tasks/tickets/sql/camunda_advance_search_ticket_count.sql` – same filters/criteria, returns total count
- `tasks/tickets/sql/camunda_advance_search_ticket_details.sql` – enrichment for a given list of process instance IDs (title/type/status/phases/processors/duration)

Operationally, deploy/update these functions in your database in the same order: **IDs → Count → Details** (IDs/Count must stay logically aligned).
