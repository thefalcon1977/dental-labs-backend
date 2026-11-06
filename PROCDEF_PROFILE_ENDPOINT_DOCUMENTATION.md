# Process Definition Profile Endpoint Documentation

## Endpoint Overview

**URL**: `GET /workflow/procdef/{proc_def_key}/profile`

**Example**: `https://post.ilabs.ir/post-search/workflow/procdef/Care_Nokia_Critical/profile`

**Purpose**: Retrieves the configuration profile for a specific process definition. A profile defines how ticket titles and ticket numbers are generated for process instances belonging to that process definition, along with organizational metadata.

---

## 1. What Is a Process Definition Profile?

A **Process Definition Profile** is a configuration record tied to a Camunda process definition key (e.g., `Care_Nokia_Critical`). It stores:

- **Naming templates** — how ticket titles and ticket numbers are dynamically generated using placeholder variables (e.g., `{{organizational_label_}} - {{business_key_}}`)
- **Organizational metadata** — prefix, label, abbreviation, and display title for the process definition
- **Audit trail** — who created/updated the profile and when

Profiles are stored in a custom table (`act_re_procdef_profile`) alongside Camunda's engine tables. A default profile is **automatically created** via a database trigger whenever a new process definition is deployed to Camunda.

---

## 2. GET Endpoint Logic

### Request

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `proc_def_key` | URL path | `string` | ✅ | The process definition key (e.g., `Care_Nokia_Critical`) |

**Authentication**: Not required for GET (read-only).

### Processing Flow

1. **Lookup profile** — Queries `act_re_procdef_profile` table by `proc_def_key_` field
2. **If not found** — Returns `404 Not Found` with message: `"Profile for process definition key 'Care_Nokia_Critical' not found"`
3. **If found** — Enriches the profile with data from the Camunda process definition table (`act_re_procdef`):
   - Fetches the **latest version** of the process definition with matching `key_`
   - Extracts `category_` from the process definition
   - Transforms `suspension_state_` from Camunda internal values (1=active, 2=suspended) to API values (1=suspendable, 0=not suspendable)
4. **Returns** the complete profile response

### Response

**Status**: `200 OK`

```json
{
  "id_": "profile_Care_Nokia_Critical_1700000000",
  "proc_def_key_": "Care_Nokia_Critical",
  "process_instance_prefix_": "CNC",
  "organizational_label_": "Care Nokia Critical",
  "ticket_title_template_": "{{organizational_label_}} - {{process_instance_prefix_}}-{{business_key_}} - {{title}}",
  "ticket_number_template_": "{{prefix}}-{{date}}-{{counter}}",
  "abbr_": "CNC",
  "display_process_title_": "Care Nokia Critical Process",
  "created_by_": "admin",
  "created_at_": "2024-12-15T10:30:00",
  "updated_by_": "admin",
  "updated_at_": "2024-12-20T14:45:00",
  "category_": "care",
  "suspension_state_": 1
}
```

### Response Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id_` | `string` | No | Unique profile identifier |
| `proc_def_key_` | `string` | No | Process definition key (business identifier) |
| `process_instance_prefix_` | `string` | Yes | Short prefix for process instances (e.g., `EMP`, `CNC`, `APR`) |
| `organizational_label_` | `string` | Yes | Organizational unit label (e.g., `HR Department`, `Care Nokia Critical`) |
| `ticket_title_template_` | `string` | No | Template string with `{{placeholder}}` variables for generating ticket titles |
| `ticket_number_template_` | `string` | Yes | Template string for generating ticket numbers (business keys) |
| `abbr_` | `string` | Yes | Abbreviation for the process definition |
| `display_process_title_` | `string` | Yes | Human-readable display title shown in the UI |
| `created_by_` | `string` | No | Username of the profile creator |
| `created_at_` | `datetime` | No | Timestamp when the profile was created |
| `updated_by_` | `string` | Yes | Username of the last editor |
| `updated_at_` | `datetime` | No | Timestamp of last update |
| `category_` | `string` | Yes | Process definition category (sourced from Camunda `act_re_procdef`) |
| `suspension_state_` | `integer` | Yes | Suspension state: `1` = suspendable (active), `0` = not suspendable (suspended) |

---

## 3. Full CRUD Operations on the Profile

The endpoint supports the complete set of CRUD operations on the same URL pattern:

### 3.1 Create Profile — `POST /{proc_def_key}/profile`

**Auth**: Required (JWT)

Creates a new profile. The `proc_def_key` in the URL must match the one in the request body. The `created_by_` field is always overridden with the authenticated user's username from the JWT token for security.

**Request Body**:
```json
{
  "proc_def_key_": "Care_Nokia_Critical",
  "process_instance_prefix_": "CNC",
  "organizational_label_": "Care Nokia Critical",
  "ticket_title_template_": "{{organizational_label_}} - {{process_instance_prefix_}}-{{business_key_}} - {{title}}",
  "ticket_number_template_": "{{prefix}}-{{date}}-{{counter}}",
  "abbr_": "CNC",
  "display_process_title_": "Care Nokia Critical Process",
  "category_": "care",
  "suspension_state_": 1
}
```

**Validations**:
- `ticket_title_template_` must contain at least one `{{placeholder}}`
- `proc_def_key_` cannot be empty
- `suspension_state_` must be `0` or `1` (if provided)
- Returns `409 Conflict` if a profile already exists for the key
- Returns `404 Not Found` if the process definition doesn't exist in Camunda

**Side Effects**:
- If `category_` or `suspension_state_` is provided, the corresponding fields are also updated in the Camunda `act_re_procdef` table (all versions with the same key)
- Audit entries are recorded for any process definition field changes

### 3.2 Update Profile — `PUT /{proc_def_key}/profile`

**Auth**: Required (JWT)

Full update of the profile. All mutable fields can be changed. The `updated_by_` is set from the JWT.

### 3.3 Partial Update — `PATCH /{proc_def_key}/profile`

**Auth**: Required (JWT)

Partial update — only fields included in the request body are updated. Same behavior as PUT but with `exclude_unset=True` semantics.

### 3.4 Delete Profile — `DELETE /{proc_def_key}/profile`

Deletes the profile. Returns a success message.

---

## 4. Template System

### 4.1 Ticket Title Template

The `ticket_title_template_` field uses `{{placeholder}}` syntax to dynamically generate ticket titles when process instances are created.

**System Variables** (always available):

| Placeholder | Description | Example Value |
|-------------|-------------|---------------|
| `{{process_instance_prefix_}}` | Prefix from the profile | `EMP` |
| `{{organizational_label_}}` | Organizational label from the profile | `HR Department` |
| `{{process_instance_id_}}` | Unique process instance ID | `12345` |
| `{{business_key_}}` | Business key of the process instance | `EMP-2024-001` |
| `{{date}}` | Current date in `YYYY-MM-DD` format | `2024-12-15` |

**Custom Variables**: Any process instance variable can be used as a placeholder (e.g., `{{title}}`, `{{username}}`, `{{request_type}}`).

**Example Templates**:
```
{{organizational_label_}} - {{process_instance_prefix_}}-{{business_key_}} - {{title}}
→ "HR Department - EMP-EMP-2024-001 - Employee Onboarding"

{{process_instance_prefix_}}-{{business_key_}} - {{request_type}}
→ "EMP-EMP-2024-001 - Access Request"

{{organizational_label_}} - {{process_instance_prefix_}}-{{process_instance_id_}} ({{date}})
→ "HR Department - EMP-12345 (2024-12-15)"
```

### 4.2 Ticket Number Template

The `ticket_number_template_` field generates business keys (ticket numbers) using similar placeholder syntax with additional system variables:

| Placeholder | Description | Example Value |
|-------------|-------------|---------------|
| `{{category}}` | Business category | `employee` |
| `{{number}}` / `{{counter}}` | Sequential number (padded to 5 digits, **resets daily at 00:00**) | `00001` |
| `{{date}}` | Current date in `YYYYMMDD` format (no dashes) | `20241215` |
| `{{timestamp}}` / `{{ts}}` | Full timestamp `YYYYMMDDHHMMSSMS` (Asia/Tehran timezone) | `20241215143025001` |
| `{{prefix}}` | Process instance prefix from profile | `EMP` |
| `{{abbr}}` | Abbreviation from profile | `HR` |
| `{{organizational_label}}` | Organizational label from profile | `HR Department` |
| `{{process_instance_id}}` | Process instance ID | `abc-123-def` |

**Example Templates**:
```
{{prefix}}-{{date}}-{{counter}}   → "EMP-20241215-00001"
{{abbr}}-{{counter}}              → "HR-00001"
{{category}}-{{timestamp}}-{{number}} → "employee-20241215143025001-00001"
```

### 4.3 Automatic Title Generation (Database Triggers)

Titles are generated **automatically** at the database level via PostgreSQL triggers:

1. **On Process Start** (`trigger_generate_title_on_start`):
   - Fires when a new process instance is inserted into `act_ru_execution`
   - Generates a title using the profile template and available variables
   - Non-blocking — generates with whatever variables are available at startup

2. **On Variable Change** (`trigger_regenerate_title_on_variable_change`):
   - Fires when process instance variables are inserted or updated in `act_ru_variable`
   - Checks if the changed variable is referenced by the title template
   - Regenerates the title with retry logic (up to 10 retries, 200ms delay) to handle race conditions
   - Skips regeneration for system variables (to avoid infinite loops)

3. **On Process Completion** (`trigger_sync_title_on_completion`):
   - Fires when a process instance is removed from the runtime table
   - Syncs the generated title from `act_ru_execution_titles` to `act_hi_procinst_titles`

### 4.4 Title Storage

Titles are stored in **separate tables** (not modifying Camunda's core tables):

| Table | Purpose |
|-------|---------|
| `act_ru_execution_titles` | Titles for **active** process instances (linked to `act_ru_execution`) |
| `act_hi_procinst_titles` | Titles for **completed/historical** process instances (linked to `act_hi_procinst`) |

---

## 5. Additional Endpoints

### 5.1 List All Profiles — `GET /workflow/procdef/profiles`

Lists all profiles with pagination and search.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `int` | `1` | Page number (min: 1) |
| `size` | `int` | `20` | Page size (min: 1, max: 100) |
| `search` | `string` | `null` | Search term (searches in `proc_def_key_`, `organizational_label_`, `ticket_title_template_`) |

### 5.2 Generate Title (Test) — `POST /workflow/procdef/{proc_def_key}/profile/generate-title`

Test endpoint to preview title generation with given variables.

**Request Body**:
```json
{
  "proc_def_key_": "Care_Nokia_Critical",
  "process_instance_id_": "12345",
  "business_key_": "CNC-2024-001",
  "variables": {
    "title": "Nokia Critical Issue",
    "username": "john.doe"
  }
}
```

**Response**:
```json
{
  "generated_title": "Care Nokia Critical - CNC-CNC-2024-001 - Nokia Critical Issue",
  "generated_number": "CNC-20241215-00001",
  "template_used": "{{organizational_label_}} - {{process_instance_prefix_}}-{{business_key_}} - {{title}}",
  "number_template_used": "{{prefix}}-{{date}}-{{counter}}",
  "variables_resolved": {
    "process_instance_prefix_": "CNC",
    "organizational_label_": "Care Nokia Critical",
    "process_instance_id_": "12345",
    "business_key_": "CNC-2024-001",
    "date": "2024-12-15",
    "title": "Nokia Critical Issue",
    "username": "john.doe"
  },
  "unresolved_placeholders": []
}
```

### 5.3 Template Info — `GET /workflow/procdef/profile/template-info`

Returns documentation about available template variables and example templates.

### 5.4 Validate Template — `POST /workflow/procdef/profile/validate-template`

Validates a template string and returns analysis (placeholder count, issues like malformed or nested placeholders).

### 5.5 Audit Trail — `GET /workflow/procdef/{proc_def_key}/profile/audit`

Returns the change history for a profile (paginated). Tracks field-level changes with old/new values, who changed it, and when.

### 5.6 Executable Versions — `GET /workflow/procdef/{proc_def_key}/executable-versions`

Lists available deployed versions of the process definition.

### 5.7 Validate Version — `POST /workflow/procdef/{proc_def_key}/profile/validate-version`

Validates whether a specific version exists for the process definition.

---

## 6. Audit System

Every change to a profile is tracked in the `act_re_procdef_profile_audit` table:

- **Database-level triggers** automatically log CREATE, UPDATE, and DELETE operations with field-by-field change tracking
- **API-level auditing** records changes to Camunda process definition fields (`category_`, `suspension_state_`) made through the profile API

Each audit record contains:
- Which profile was changed (`profile_id_`, `proc_def_key_`)
- Which field changed (`field_name_`)
- The old and new values
- Who made the change (`changed_by_`)
- When (`changed_at_`)
- Change type (`CREATE`, `UPDATE`, `DELETE`)
- Human-readable description

---

## 7. Auto-Profile Creation

When a new process definition is deployed to Camunda (inserted into `act_re_procdef`), a database trigger (`trigger_create_profile_on_procdef_creation`) **automatically creates a default profile** with:

- Prefix: `DEFAULT`
- Organizational label: `Default Organization`
- Title template: `{{organizational_label}} - {{process_instance_prefix}}-{{business_key}} - {{date}}`
- No ticket number template

This ensures every process definition always has a profile, which can then be customized via the API.

---

## 8. Error Responses

| Status | Code | Scenario |
|--------|------|----------|
| `200` | OK | Profile found and returned |
| `201` | Created | Profile successfully created (POST) |
| `400` | Bad Request | URL key doesn't match body key, or invalid template |
| `404` | Not Found | No profile exists for the given `proc_def_key` |
| `409` | Conflict | Profile already exists (on create) |

**Error Response Format**:
```json
{
  "detail": "Profile for process definition key 'Care_Nokia_Critical' not found"
}
```

---

## 9. Database Schema Summary

| Table | Purpose |
|-------|---------|
| `act_re_procdef_profile` | Profile configuration (templates, labels, prefix) |
| `act_re_procdef_profile_audit` | Audit trail for profile changes |
| `act_ru_execution_titles` | Generated titles for active process instances |
| `act_hi_procinst_titles` | Generated titles for completed process instances |
| `act_re_procdef` | Camunda's process definition table (read + updated for category/suspension) |

---

## 10. Summary

The `GET /workflow/procdef/{proc_def_key}/profile` endpoint retrieves a **process definition profile** — a configuration that controls:

1. **How ticket titles are generated** — via a template with `{{placeholder}}` variables resolved from profile metadata and process instance variables
2. **How ticket numbers (business keys) are generated** — via a separate template with counters, dates, and timestamps
3. **Organizational metadata** — prefix, label, abbreviation, and display title
4. **Process definition control** — category and suspension state (synced to Camunda)

The system is fully automated: profiles are auto-created on deployment, titles are auto-generated via database triggers, and all changes are audited.
