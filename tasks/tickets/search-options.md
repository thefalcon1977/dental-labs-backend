# Search Options Implementation Documentation

## Overview

This document provides a comprehensive business-level guide for the **Search Options** endpoint: `GET /workflow-engine/tickets/search/options/{process_definition_id}`. It describes all logic, data sources, response assembly, and behavior without code implementation details. The endpoint powers dropdowns and field selectors in the ticket search UI by returning process-definition-specific metadata: general columns, basic information (start event), activities (user tasks and start event), form fields, variables, and presets.

---

## 1. ENDPOINT CONTRACT

### 1.1 HTTP Method and Path

- **Method:** GET
- **Path:** `/workflow-engine/tickets/search/options/{process_definition_id}`
- **Purpose:** Return search UI options for a specific process definition (dropdowns, column lists, form fields, variables, presets).

### 1.2 Path Parameters

| Parameter                 | Type   | Required | Description                                      |
|---------------------------|--------|----------|--------------------------------------------------|
| `process_definition_id`   | string | Yes      | Process definition ID (e.g. from Camunda engine). |

### 1.3 Query Parameters

- None. All input is via the path parameter.

### 1.4 Authentication

- No explicit auth is enforced in the endpoint description; in practice the app may require JWT or session for `/workflow-engine/*`. Not covered here.

### 1.5 Response

- **Success:** 200 OK, JSON body (see Section 6).
- **No process definition:** 200 OK with a safe default payload (empty activities, default basic_information, same top-level keys).
- **Errors:** Exceptions may surface as 500; database or BPMN parsing failures are logged and can result in partial or default payloads.

---

## 2. DATA SOURCES

### 2.1 Process Definition (Validation)

- **Table:** Process Definition (e.g. `act_re_procdef` or equivalent).
- **Usage:** Check existence by `id_ == process_definition_id`.
- **Behavior:** If no row exists, return immediately with the default response (no BPMN parsing, no activities). If exists, proceed to load BPMN and forms.

### 2.2 BPMN Definition

- **Source:** Deployment resource linked to the process definition (e.g. `act_ge_bytearray` / DeploymentResource), keyed by process definition’s deployment ID and resource name.
- **Usage:** Fetch BPMN XML for the given process definition, then parse to obtain activities (events, user tasks, etc.) and their attributes (formRef/formKey, assignee, candidates, listeners, input/output, etc.).
- **Encoding:** BPMN bytes decoded as UTF-8.

### 2.3 Form Definitions

- **Source:** Deployment resources (form JSON files) in the same deployment or, when using form-ref binding “latest”, from Camunda Form Definition table (latest version by form key across deployments).
- **Usage:** Resolve form by `form_ref` or `form_key` from BPMN, then decode form JSON to extract fields (key, label, type, options, dropdown_config).
- **Schema support:** Camunda Form (components), JSON Schema (properties), or generic (fields/components/items or top-level keys).

### 2.4 Constants and Conventions

- **Start event as “Basic Information”:** Start event is singled out and exposed as `basic_information` and also as the first entry under `activities` with specific IDs and display names.
- **IDs:**
  - Basic-information block: original start event ID + suffix (e.g. `__basic_information`).
  - Start-event activity entry: original start event ID + history suffix (e.g. none).
- **Display name:** Start event is labeled with a fixed display name (e.g. “Basic Information”) in both basic_information and activity list.
- **Sources:** Basic-information block is tagged with a “basic_information” source; start-event activity is tagged with a “start_event_history” source.

---

## 3. ACTIVITY SELECTION AND TYPES

### 3.1 Activity Types Included

Only the following BPMN activity types are included in the response:

- **startEvent**
- **userTask**

All other types (endEvent, serviceTask, scriptTask, gateways, callActivity, subProcess, etc.) are excluded from the options payload.

### 3.2 Activity Source and Order

- Activities are obtained by parsing the process definition’s BPMN XML (element order and/or execution order).
- **Start event:** One start event is identified and used for:
  - `basic_information` (with decorated id/name/source/key).
  - First item in `activities` (with history id/name/source).
- **User tasks:** All user tasks appear in `activities` after the start-event entry, in the same order as produced by the BPMN parser (e.g. execution or XML order).

### 3.3 Execution Order (Optional)

- The BPMN parser may assign an execution order to activities (e.g. from sequence flows and topology). Search options may preserve this order when building the activity list; the exact algorithm (e.g. topological sort, XML index) is an implementation detail.

---

## 4. FORM FIELDS

### 4.1 When Form Fields Are Loaded

- For each activity (start event or user task) that has a form reference:
  - **form_ref** (Camunda 7+) or **form_key** is read from the BPMN element.
- If neither form_ref nor form_key is present, the activity’s `form_fields` list is empty.

### 4.2 Form Resource Resolution

**Within deployment (default binding):**

- Resolve form resource in the process definition’s deployment.
- Candidate names: `form_ref`, `form_ref.json`, `form_ref.form`, `form_ref.schema.json`.
- Try exact name match first, then partial (e.g. `ILIKE %form_ref%`), then optional deep scan of JSON/form resources in the deployment matching schema id/key to form_ref.

**Latest binding (`form_ref_binding == "latest"`):**

- Use Camunda Form Definition table: find latest version by form key across all deployments.
- Then resolve the deployment resource by that deployment ID and resource name.
- If no form definition or resource is found, form fields for that activity are empty.

### 4.3 Form Schema Decoding

- Form resource bytes are decoded (e.g. UTF-8 or latin-1).
- JSON is parsed. Schema type is detected (e.g. camundaForm, jsonSchema, generic).
- **Camunda Form:** Fields extracted from `components` (including nested groups); key, label, type, options, dropdown_config, etc.
- **JSON Schema:** Fields from `properties` (key, title, type, default, enum).
- **Generic:** From `fields` / `components` / `items` or top-level keys.
- Decoding/parse failures: treat as no form; activity gets empty `form_fields`.

### 4.4 Normalized Form Field Shape

For each field, expose at least:

- **key** – field key (or id).
- **label** – display label.
- **type** – field type (string, datetime, select, etc.).
- **possible_values** – for select/radio/checklist (from form schema options).
- **dropdown_config** – for dropdown type (if present in schema).

Null/absent values can be omitted. Only key/label/type are required for search UI; possible_values and dropdown_config support dropdowns and filters.

### 4.5 Start Event Form Fields

- If the chosen start event has a form, its form fields are loaded the same way and attached to `basic_information` and to the start-event activity entry.
- If the start event is found but form_fields are initially empty, the implementation may retry form extraction once (e.g. re-fetch activities and re-resolve form) and log success or failure.

---

## 5. VARIABLES

### 5.1 Variable Sources per Activity

Variables listed for an activity are derived from one or more of:

- **Task listeners** – configuration and expressions (e.g. `${variableName}`).
- **Execution listeners** – same.
- **Input/output parameters** – BPMN extension input/output, connector in/out, call activity variable mapping.
- **Variable mapping** – source/target expressions.
- **Properties** – activity or extension properties containing expressions.
- **Scripts** – simple patterns (e.g. var/let/const, assignments).
- **Expressions** – `${...}` and `#{...}` parsed to extract variable names; built-in names (e.g. execution.*, task.*, dateTime()) are excluded.
- **Optional:** Direct BPMN parsing or known activity-id mappings for specific process definitions (fallback or legacy).

### 5.2 Exclusion of Form Field Keys

- Any variable name that equals a form field **key** for that same activity is removed from the variables list.
- Purpose: avoid duplicating in “variables” what is already in “form_fields”.

### 5.3 Variable Output Shape

- Each variable is exposed as an object: `{"name": "<var_name>", "type": "string"}` (type may be defaulted to string).
- List is sorted (e.g. by name) for stable ordering.

---

## 6. RESPONSE STRUCTURE

### 6.1 Top-Level Keys

- **general_information** – list of core column definitions (name + type).
- **basic_information** – single object: start-event block or empty default.
- **activities** – list of activity objects (start event first, then user tasks).
- **activity_fields** – list of activity field names usable for search (e.g. name, type, state, assignee, start_time, end_time, duration).
- **presets** – list of column preset names (e.g. minimal, standard, performance, full).
- **professional_selection** – list of professional/advanced column identifiers (e.g. activities.summary, activities.active, activities.completed, age_hours, progress_percent).

### 6.2 general_information

- Fixed list of column descriptors: `{ "name": "<field_name>", "type": "<type>" }`.
- Includes at least: ticket_number, ticket_type, ticket_title, creator, creator_main_group, create_time, end_time, process_duration, ticket_status, ticket_phases, current_processors, sub_ticket, associated.
- Types: string, datetime, integer, select, related_tickets, etc., as defined by the implementation.

### 6.3 basic_information

**When a start event exists:**

- **id** – start event id with basic-information suffix (e.g. `StartEvent_1__basic_information`).
- **key** – same as id.
- **name** / **display_name** – fixed label (e.g. “Basic Information”).
- **original_id** / **original_name** – raw BPMN id and name.
- **type** – `"startEvent"`.
- **source** – e.g. `"basic_information"`.
- **start_time**, **end_time**, **duration**, **state** – optional; may be null.
- **form_fields** – list of normalized form fields (see 4.4).
- **variables** – list of variable objects (see 5.3).

**When no start event (or process definition missing):**

- **id**: null.
- **name** / **display_name**: same fixed “Basic Information” label.
- **type**: `"startEvent"`.
- **form_fields**: [].
- **variables**: [].
- **source**, **original_id**, **original_name** set as per constants.

### 6.4 activities

- **First element:** Start event activity (if any), with history id, source `"start_event_history"`, and same form_fields/variables as basic_information.
- **Remaining elements:** User tasks only, each with:
  - **id**, **name**, **type** (`"userTask"`), **start_time**, **end_time**, **duration**, **state**
  - **form_fields**, **variables**
  - Optional: assignee, candidate_users, candidate_groups, form_key, form_ref, due_date, priority, task_listeners, etc., if exposed by the implementation.

### 6.5 activity_fields

- Fixed list of field names, e.g.: `["name", "type", "state", "assignee", "start_time", "end_time", "duration"]`.
- Used by the UI to build activity-based filters or column selectors.

### 6.6 presets and professional_selection

- **presets:** e.g. `["minimal", "standard", "performance", "full"]`.
- **professional_selection:** e.g. `["activities.summary", "activities.active", "activities.completed", "age_hours", "progress_percent"]`.
- Same structure whether the process definition exists or not.

---

## 7. ERROR AND EDGE BEHAVIOR

### 7.1 Missing Process Definition

- Return 200 with default payload: general_information and activity_fields as usual; basic_information empty/default; activities []; presets and professional_selection as usual.

### 7.2 BPMN Load or Parse Errors

- Log warning/error.
- Treat as no activities: activities = [], basic_information = empty default.
- Rest of response (general_information, activity_fields, presets, professional_selection) unchanged.

### 7.3 Form Resolution or Decode Failures

- Per activity: if form_ref/form_key resolution or form JSON decode fails, that activity’s form_fields = [].
- No failure propagated to the whole response.

### 7.4 Start Event Form Retry

- If start event is found but form_fields are empty, implementation may retry form extraction once (e.g. re-fetch BPMN activities, re-resolve form).
- Success/failure logged; response still returned.

### 7.5 Variable Extraction Failures

- If variable extraction fails for an activity, use empty variables list for that activity.
- Do not fail the entire request.

---

## 8. PERFORMANCE AND CACHING

### 8.1 Database and I/O

- One query to validate process definition.
- One (or more) read of deployment resource(s) for BPMN XML and form JSON.
- Optional use of Camunda Form Definition when form_ref_binding is “latest”.
- No requirement to cache; if caching is added, process definition and deployment resources are good candidates (invalidated on deployment/version change).

### 8.2 BPMN Parsing

- Parsing is in-memory (XML parse + activity extraction + optional execution order).
- Form decoding is per-activity, only for activities that have form_ref/form_key.

---

## 9. IMPLEMENTATION TASKS (CHECKLIST)

1. **Validation** – Resolve process definition by id; if missing, return default response.
2. **BPMN load** – Load BPMN XML for the process definition from deployment resources.
3. **Activity parsing** – Parse BPMN to list activities; filter to startEvent and userTask; preserve order.
4. **Start event** – Identify single start event; build basic_information block and start-event activity entry with correct ids/sources/display names.
5. **Form resolution** – For each activity with form_ref/form_key: resolve resource (deployment or latest); decode JSON; normalize fields; attach to activity and basic_information where applicable.
6. **Form field normalization** – Emit key, label, type; add possible_values for select-like types; add dropdown_config for dropdowns.
7. **Variable extraction** – From listeners, in/out params, expressions, scripts; exclude form field keys; emit { name, type } list per activity.
8. **Response assembly** – general_information, basic_information, activities (start event + user tasks), activity_fields, presets, professional_selection.
9. **Error handling** – Graceful degradation for missing proc def, BPMN errors, form errors, variable errors; log and return partial/default payloads.
10. **Tests** – Cover: missing process definition, valid BPMN with start + user tasks, form resolution (deployment and latest), empty form_fields, variable extraction and form-key exclusion, response shape (including activity_fields and presets).

---

## 10. SUMMARY

- **Endpoint:** `GET /workflow-engine/tickets/search/options/{process_definition_id}`.
- **Purpose:** Provide search UI options (columns, basic information, activities, form fields, variables, presets) for one process definition.
- **Data:** Process definition existence; BPMN XML; form JSON from deployment or Camunda Form Definition (latest).
- **Activities:** Only startEvent and userTask; start event drives basic_information and first activity entry.
- **Forms:** Resolved by form_ref/form_key; decoded and normalized; key, label, type, possible_values, dropdown_config.
- **Variables:** From listeners, in/out, expressions, scripts; form field keys excluded; output { name, type }.
- **Robustness:** Missing proc def or BPMN/form errors yield safe default or partial response; no unhandled failure for the whole endpoint.

---

## 11. RESPONSE STRUCTURE (JSON EXAMPLE)

### 11.1 Success Response (Process Definition Exists)

```json
{
  "general_information": [
    {"name": "ticket_number", "type": "string"},
    {"name": "ticket_type", "type": "string"},
    {"name": "ticket_title", "type": "string"},
    {"name": "creator", "type": "string"},
    {"name": "creator_main_group", "type": "select"},
    {"name": "create_time", "type": "datetime"},
    {"name": "end_time", "type": "datetime"},
    {"name": "process_duration", "type": "integer"},
    {"name": "ticket_status", "type": "string"},
    {"name": "ticket_phases", "type": "select"},
    {"name": "current_processors", "type": "select"},
    {"name": "sub_ticket", "type": "related_tickets"},
    {"name": "associated", "type": "related_tickets"}
  ],
  "basic_information": {
    "id": "StartEvent_1__basic_information",
    "key": "StartEvent_1__basic_information",
    "name": "Basic Information",
    "display_name": "Basic Information",
    "original_id": "StartEvent_1",
    "original_name": "Start",
    "type": "startEvent",
    "source": "basic_information",
    "start_time": null,
    "end_time": null,
    "duration": null,
    "state": null,
    "form_fields": [
      {"key": "employee_name", "label": "Employee Name", "type": "string"},
      {"key": "leave_type", "label": "Leave Type", "type": "select", "possible_values": ["annual", "sick"]}
    ],
    "variables": []
  },
  "activities": [
    {
      "id": "StartEvent_1",
      "key": "StartEvent_1",
      "name": "Start",
      "display_name": "Start",
      "type": "startEvent",
      "source": "start_event_history",
      "form_fields": [...],
      "variables": []
    },
    {
      "id": "Activity_submit_request",
      "name": "Submit Request",
      "type": "userTask",
      "form_fields": [...],
      "variables": [{"name": "leave_type", "type": "string"}]
    }
  ],
  "activity_fields": [
    "name",
    "type",
    "state",
    "assignee",
    "start_time",
    "end_time",
    "duration"
  ],
  "presets": ["minimal", "standard", "performance", "full"],
  "professional_selection": [
    "activities.summary",
    "activities.active",
    "activities.completed",
    "age_hours",
    "progress_percent"
  ]
}
```

### 11.2 Default Response (Process Definition Missing)

- Same top-level keys.
- `basic_information`: id null, name/display_name "Basic Information", type startEvent, form_fields [], variables [].
- `activities`: [].

---

## 12. USAGE IN SEARCH UI

- **general_information** – Drives column picker / filter list for core ticket fields (ticket_number, creator, create_time, etc.).
- **basic_information** – Represents “Basic Information” (start form) in the UI: form_fields and variables used for filters and column selection.
- **activities** – Each entry (start event + user tasks) provides activity id/name, form_fields, and variables for activity-scoped filters and projections (e.g. heavy search field paths).
- **activity_fields** – List of activity attributes (name, type, state, assignee, start_time, end_time, duration) for building activity conditions.
- **presets** / **professional_selection** – Column preset names and advanced column identifiers for quick column sets in advance/heavy search.

---

This document is the single reference for reimplementing or validating the business behavior of the Search Options endpoint.
