# Form Templates API Implementation Documentation

## Overview
This document provides a comprehensive business-level guide for implementing the form templates functionality. It covers all logic, filters, permissions, CRUD operations, and data structures without any code implementation details.

The Form Templates API allows users to save, manage, and reuse form field values for Camunda forms. Templates can be private (visible only to creator) or public (shared with all users), and include categorization, tagging, and usage tracking. Multiple templates per form per user are supported.

---

## 1. BASE DATA STRUCTURE

### 1.1 Data Source
The form templates functionality uses a single data source:

**Form Templates Table (act_re_form_template)**
- Contains all saved form field value templates
- Stores form field values as JSONB
- Includes metadata: name, description, category, tags, sharing settings
- References Camunda form definitions (form_key, form_id, form_version)
- Tracks usage statistics and timestamps
- Supports soft deletion and multi-tenancy
- Follows Camunda naming conventions (act_re_ prefix, _ suffix)

### 1.2 Core Data Fields

**Primary Identification:**
- id_: String primary key in Camunda format (e.g., "form-template-{uuid}")
- rev_: Revision number for optimistic locking (integer, default: 1)
- name_: Template name (required, max 255 characters)
- description_: Optional description text (max 1000 characters)

**Form Reference:**
- form_key_: Camunda form key identifier (required, max 255 characters)
  - References act_re_camformdef.key_
  - Identifies which form this template is for
- form_id_: Camunda form ID (optional, max 64 characters)
  - References act_re_camformdef.id_
  - Used for version-specific templates
- form_version_: Camunda form version (optional, integer)
  - References act_re_camformdef.version_
  - Used for version-specific templates

**Ownership:**
- created_by_: Username of template creator (required, max 100 characters)
- modified_by_: Username of last modifier (optional, max 100 characters)

**Template Content:**
- form_data_: Form field values stored as JSONB (required)
  - Contains: field names and their values as key-value pairs
  - Required field - must be non-empty dictionary
  - Example: {"leaveType": "annual", "startDate": "2025-01-15", "duration": 5}

**Sharing and Visibility:**
- is_public_: Boolean flag indicating if template is shared with all users
  - false: Private template (only visible to creator)
  - true: Public template (visible to all users)

**Categorization:**
- category_: Optional category name for organizing templates (max 100 characters)
- tags_: Optional array of tag strings stored as JSONB
  - Maximum 20 tags per template
  - Each tag maximum 50 characters

**Usage Tracking:**
- usage_count_: Integer counter for number of times template has been used
- last_used_at_: Timestamp of most recent execution (nullable)

**Timestamps:**
- created_at_: Timestamp when template was created (auto-set on creation)
- updated_at_: Timestamp when template was last updated (auto-updated on modification)
- modified_at_: Timestamp when template was last modified (set on update, nullable)

**Soft Delete:**
- is_deleted_: Boolean flag for soft deletion (default: false)
- deleted_at_: Timestamp when template was soft deleted (nullable)

**Multi-Tenancy:**
- tenant_id_: Optional tenant identifier for multi-tenant isolation (max 64 characters)

---

## 2. ENDPOINTS

### 2.1 POST `/forms/templates/`
**Purpose:** Create a new form template

**Authentication:** Required (JWT token)

**Request Body:** FormTemplateCreate schema

**Business Logic:**
1. Validate template data (name, description, form_key, form_data structure)
2. Check for duplicate template name for same user, form_key, and tenant
3. Generate unique template ID in Camunda format (form-template-{uuid})
4. Create new template record with provided data
5. Set created_by to current authenticated user
6. Initialize rev_ to 1 (first revision)
7. Initialize usage_count to 0
8. Set timestamps (created_at, updated_at)
9. Return created template with all fields

**Validation Rules:**
- name: Required, 1-255 characters
- description: Optional, max 1000 characters
- form_key: Required, 1-255 characters
- form_id: Optional, max 64 characters
- form_version: Optional, integer
- form_data: Required, must be non-empty dictionary
- tags: Optional, max 20 tags, each max 50 characters
- category: Optional, max 100 characters
- tenant_id: Optional, max 64 characters

**Duplicate Check:**
- Check if template with same name exists for current user AND same form_key
- Consider tenant_id in duplicate check:
  - If tenant_id provided: Check templates with same tenant_id
  - If tenant_id not provided: Check templates with NULL tenant_id
- Only check non-deleted templates (is_deleted_ = false)
- Same name allowed for different form_keys (multiple templates per form per user)
- If duplicate found, return 400 error

**ID Generation:**
- Generate unique string ID in Camunda format
- Format: "form-template-{12-character-hex-uuid}"
- Example: "form-template-a1b2c3d4e5f6"

**Response:** 201 Created with FormTemplateResponse

**Error Responses:**
- 400: Validation error or duplicate name
- 500: Internal server error

---

### 2.2 GET `/forms/templates/`
**Purpose:** List form templates with filtering and pagination

**Authentication:** Required (JWT token)

**Query Parameters:**
- form_key: Optional filter by form key (exact match)
- category: Optional filter by category (exact match)
- tags: Optional comma-separated list of tags (any match)
- search_term: Optional search in name and description (partial match)
- is_public: Optional filter by public/private (boolean)
- created_by: Optional filter by creator username (exact match)
- limit: Results per page (default: 50, min: 1, max: 200)
- offset: Number of results to skip (default: 0, min: 0)
- sort_by: Field to sort by (default: "created_at")
- sort_order: Sort direction "asc" or "desc" (default: "desc")

**Business Logic:**
1. Start with base query filtering out soft-deleted templates (is_deleted_ = false)
2. Apply tenant filtering if tenant_id provided
3. Apply form_key filtering if provided (exact match)
4. Apply visibility filtering based on current user:
   - If user authenticated: Show templates where (is_public_ = true OR created_by_ = user)
   - If no user: Show only public templates (is_public_ = true)
5. Apply optional filters:
   - category: Exact match on category_ field
   - tags: Match any of provided tags using JSONB contains operator
   - search_term: Partial match (ILIKE) on name_ or description_
   - is_public: Exact match on is_public_ field
   - created_by: Exact match on created_by_ field
6. Calculate total count of matching templates
7. Normalize sort_by field name (map API field names to model field names with underscore)
8. Apply sorting by specified field and order
9. Apply pagination (limit and offset)
10. Return paginated results with metadata

**Visibility Rules:**
- Users see their own templates (created_by_ = user) plus all public templates
- Public templates are visible to all authenticated users
- Private templates are only visible to their creator
- If no user authenticated, only public templates are shown

**Form Key Filtering:**
- Filter by specific Camunda form key
- Exact match on form_key_ field
- Useful for showing templates for a specific form only

**Tag Filtering:**
- Tags parameter is comma-separated string (e.g., "leave,approval")
- Split into list of individual tags
- Match if template contains ANY of the provided tags
- Uses PostgreSQL JSONB @> (contains) operator
- Only matches templates where tags_ field is not NULL
- Case-sensitive tag matching

**Search Term Filtering:**
- Searches in template name and description fields
- Uses case-insensitive partial matching (ILIKE)
- Pattern: %{search_term}%
- Matches if search term appears anywhere in name_ OR description_

**Sort Field Normalization:**
- API accepts field names without underscore (e.g., "created_at")
- Model uses field names with underscore (e.g., "created_at_")
- Normalize sort_by parameter to match model attribute names
- Mapping: created_at → created_at_, updated_at → updated_at_, etc.
- If field already has underscore, use as-is
- If field not in mapping, append underscore

**Sorting:**
- Default sort: created_at_ descending (newest first)
- Supported sort fields: Any field on FormTemplate model
- Common fields: created_at_, updated_at_, modified_at_, name_, form_key_, category_, usage_count_, last_used_at_
- Sort order: "asc" or "desc" (case-insensitive)
- Invalid sort fields return validation error

**Response:** 200 OK with FormTemplateListResponse

**Error Responses:**
- 400: Invalid sort field
- 500: Internal server error

---

### 2.3 GET `/forms/templates/{template_id}`
**Purpose:** Get a specific template by ID

**Authentication:** Required (JWT token)

**Path Parameters:**
- template_id: String template ID (Camunda format)

**Business Logic:**
1. Query template by ID (string, not integer)
2. Exclude soft-deleted templates (is_deleted_ = false)
3. Apply tenant filtering if tenant_id provided
4. Check permissions:
   - If template is public: Allow access
   - If template is private: Only allow if created_by_ = current user
   - If access denied: Return 404 (not found) to prevent information leakage
5. Return template data

**Permission Rules:**
- Public templates: Accessible by all authenticated users
- Private templates: Only accessible by creator
- If user doesn't have access, return 404 (not found) instead of 403
- This prevents information leakage about template existence

**Response:** 200 OK with FormTemplateResponse

**Error Responses:**
- 404: Template not found or access denied
- 500: Internal server error

---

### 2.4 PUT `/forms/templates/{template_id}`
**Purpose:** Update an existing template

**Authentication:** Required (JWT token)

**Path Parameters:**
- template_id: String template ID (Camunda format)

**Request Body:** FormTemplateUpdate schema (all fields optional)

**Business Logic:**
1. Get template by ID (with permission check)
2. Verify user is the creator (created_by_ = current user)
3. If name is being updated:
   - Check for duplicate name for same user, same form_key, and tenant
   - Only check other templates (exclude current template)
4. Update only provided fields (partial update)
5. Set modified_by_ to current user
6. Set modified_at_ to current timestamp
7. Update updated_at_ timestamp
8. Increment rev_ (revision number) for optimistic locking
9. Return updated template

**Update Rules:**
- Only creator can update template
- Partial update: Only update fields provided in request
- If name updated: Check for duplicate name (same user, same form_key, same tenant, different template)
- Duplicate check uses same logic as create (considers tenant_id and form_key)
- form_data validation: If provided, must be dictionary (can be empty)
- tags validation: If provided, must meet tag constraints (max 20, each max 50 chars)
- Revision tracking: rev_ incremented on each update

**Field Mapping:**
- API field names (without underscore) mapped to model field names (with underscore)
- Mapping: name → name_, description → description_, form_data → form_data_, etc.

**Response:** 200 OK with FormTemplateResponse

**Error Responses:**
- 404: Template not found
- 403: User is not the creator
- 400: Validation error or duplicate name
- 500: Internal server error

---

### 2.5 DELETE `/forms/templates/{template_id}`
**Purpose:** Delete a template (soft or hard delete)

**Authentication:** Required (JWT token)

**Path Parameters:**
- template_id: String template ID (Camunda format)

**Query Parameters:**
- hard_delete: Boolean flag (default: false)
  - false: Soft delete (set is_deleted_ = true, set deleted_at_ timestamp)
  - true: Hard delete (permanently remove from database)

**Business Logic:**
1. Get template by ID (with permission check)
2. Verify user is the creator (created_by_ = current user)
3. Perform deletion:
   - If hard_delete = false: Set is_deleted_ = true, set deleted_at_ = current timestamp, increment rev_
   - If hard_delete = true: Permanently delete record from database
4. Commit changes
5. Return 204 No Content

**Deletion Rules:**
- Only creator can delete template
- Soft delete by default (preserves data, hides from queries)
- Hard delete permanently removes template
- Soft-deleted templates are excluded from all list/get queries
- Hard delete is irreversible
- Revision tracking: rev_ incremented on soft delete

**Response:** 204 No Content

**Error Responses:**
- 404: Template not found
- 403: User is not the creator
- 500: Internal server error

---

## 3. FILTERS

### 3.1 Filter Application Rules
- All filters are applied at SQL level using WHERE clauses
- Filters are combined with AND logic (all must match)
- Filters are optional - if not provided, filter is skipped
- Filters are case-sensitive for exact matches (category, created_by, form_key)
- Filters are case-insensitive for text searches (search_term)

### 3.2 Form Key Filter
- **Parameter:** form_key (optional string)
- **Type:** Exact match
- **Field:** FormTemplate.form_key_
- **Logic:** form_key_ == provided_value
- **Case Sensitivity:** Case-sensitive
- **Purpose:** Filter templates for a specific Camunda form
- **Use Case:** Show only templates for a specific form

### 3.3 Category Filter
- **Parameter:** category (optional string)
- **Type:** Exact match
- **Field:** FormTemplate.category_
- **Logic:** category_ == provided_value
- **Case Sensitivity:** Case-sensitive
- **NULL Handling:** Only matches templates with non-NULL category

### 3.4 Tags Filter
- **Parameter:** tags (optional comma-separated string)
- **Type:** Array contains (any match)
- **Field:** FormTemplate.tags_ (JSONB array)
- **Logic:** Template tags array contains ANY of the provided tags
- **Implementation:**
  - Split comma-separated string into list
  - Use PostgreSQL JSONB @> (contains) operator
  - Check: tags_ @> [tag] for each provided tag
  - Match if ANY tag matches (OR logic within filter)
- **Case Sensitivity:** Case-sensitive
- **NULL Handling:** Only matches templates where tags_ is not NULL

### 3.5 Search Term Filter
- **Parameter:** search_term (optional string)
- **Type:** Partial match (contains)
- **Fields:** FormTemplate.name_, FormTemplate.description_
- **Logic:** name_ ILIKE %search_term% OR description_ ILIKE %search_term%
- **Case Sensitivity:** Case-insensitive (ILIKE)
- **Pattern:** %{search_term}% (matches anywhere in field)

### 3.6 Public/Private Filter
- **Parameter:** is_public (optional boolean)
- **Type:** Exact match
- **Field:** FormTemplate.is_public_
- **Logic:** is_public_ == provided_value
- **Values:** true (public), false (private)

### 3.7 Creator Filter
- **Parameter:** created_by (optional string)
- **Type:** Exact match
- **Field:** FormTemplate.created_by_
- **Logic:** created_by_ == provided_value
- **Case Sensitivity:** Case-sensitive
- **Use Case:** Filter to see only templates created by specific user

### 3.8 Tenant Filter (Implicit)
- **Parameter:** tenant_id (from authenticated user context)
- **Type:** Exact match
- **Field:** FormTemplate.tenant_id_
- **Logic:** Applied automatically based on user's tenant context
- **Behavior:**
  - If tenant_id provided: Only show templates with matching tenant_id_
  - If tenant_id not provided: Only show templates with NULL tenant_id_
- **Purpose:** Multi-tenant data isolation

### 3.9 Visibility Filter (Implicit)
- **Parameter:** user (from authenticated user context)
- **Type:** Complex logic
- **Logic:**
  - If user authenticated: (is_public_ == true OR created_by_ == user)
  - If no user: (is_public_ == true)
- **Purpose:** Ensure users only see templates they have access to

### 3.10 Soft Delete Filter (Implicit)
- **Parameter:** Always applied
- **Type:** Exact match
- **Field:** FormTemplate.is_deleted_
- **Logic:** is_deleted_ == false
- **Purpose:** Exclude soft-deleted templates from all queries

---

## 4. PERMISSIONS AND ACCESS CONTROL

### 4.1 Permission Model Overview
The form templates system uses a simple but effective permission model based on ownership and sharing settings.

### 4.2 Permission Rules

**Rule 1: Template Ownership**
- Template creator (created_by_) has full access to their templates
- Creator can view, update, and delete their own templates
- Ownership is determined by created_by_ field matching current user

**Rule 2: Public Templates**
- Templates with is_public_ = true are visible to all authenticated users
- All users can view public templates
- Only creator can update or delete public templates

**Rule 3: Private Templates**
- Templates with is_public_ = false are only visible to creator
- Other users cannot see, access, or use private templates
- Access attempts return 404 (not found) to prevent information leakage

**Rule 4: Update Permissions**
- Only template creator can update template
- Attempts by non-creators return 403 (forbidden)
- Update includes: name, description, form_data, is_public, category, tags

**Rule 5: Delete Permissions**
- Only template creator can delete template
- Attempts by non-creators return 403 (forbidden)
- Creator can choose soft delete or hard delete

### 4.3 Multi-Tenancy Support
- Templates can be associated with tenant_id_
- Users only see templates from their tenant
- Tenant isolation is enforced at query level
- Templates with NULL tenant_id_ are visible to users with NULL tenant_id_

### 4.4 Information Leakage Prevention
- Access denied scenarios return 404 (not found) instead of 403
- Prevents attackers from discovering template existence
- Applies to: get, update, delete operations
- Only creator knows if template exists if it's private

---

## 5. SORTING

### 5.1 Sort Parameters
- sort_by: Field to sort by (default: "created_at")
- sort_order: "asc" or "desc" (default: "desc")

### 5.2 Sort Field Normalization
- API accepts field names without underscore (e.g., "created_at")
- Model uses field names with underscore (e.g., "created_at_")
- Normalize sort_by parameter to match model attribute names
- Mapping includes:
  - created_at → created_at_
  - updated_at → updated_at_
  - modified_at → modified_at_
  - last_used_at → last_used_at_
  - form_key → form_key_
  - form_id → form_id_
  - form_version → form_version_
  - created_by → created_by_
  - modified_by → modified_by_
  - is_public → is_public_
  - category → category_
  - tags → tags_
  - usage_count → usage_count_
  - name → name_
  - description → description_
  - tenant_id → tenant_id_
- If field already has underscore, use as-is
- If field not in mapping, append underscore

### 5.3 Supported Sort Fields
Any field on the FormTemplate model can be used for sorting. Common fields:

**created_at_**
- Sort by template creation timestamp
- Default sort field
- Useful for: Recent templates first

**updated_at_**
- Sort by last update timestamp
- Useful for: Recently modified templates

**modified_at_**
- Sort by last modification timestamp
- Useful for: Recently modified templates (explicit modification)

**name_**
- Sort alphabetically by template name
- Useful for: Alphabetical organization

**form_key_**
- Sort by Camunda form key
- Useful for: Grouping by form

**usage_count_**
- Sort by number of times template has been used
- Useful for: Most popular templates

**last_used_at_**
- Sort by last execution timestamp
- Useful for: Recently used templates

### 5.4 Sorting Implementation
- Sorting is applied at SQL level using ORDER BY
- Dynamic field selection based on normalized sort_by parameter
- Sort order: ASC or DESC based on sort_order parameter
- Applied after filtering but before pagination
- Invalid sort fields return validation error

### 5.5 Sort Order Handling
- Default to "desc" if not specified
- Case-insensitive comparison ("asc", "desc", "ASC", "DESC")
- Invalid sort_order values may cause errors

---

## 6. PAGINATION

### 6.1 Pagination Parameters
- limit: Number of items per page (default: 50, min: 1, max: 200)
- offset: Number of items to skip (default: 0, min: 0)

### 6.2 Pagination Strategy

**Two-Phase Approach:**
1. **Phase 1: Filter, Sort, and Count**
   - Apply all filters to template query
   - Apply sorting
   - Calculate total count of matching templates

2. **Phase 2: Paginate**
   - Apply LIMIT and OFFSET to sorted results
   - Execute query to fetch paginated subset
   - Return paginated results with metadata

### 6.3 Total Count Calculation
- Calculate total count after all filters are applied
- Count all matching templates before pagination
- Return total count with paginated results
- Used to calculate has_more flag

### 6.4 Has More Flag
- Calculate as: (offset + limit) < total_count
- Indicates if more pages are available
- Returned in response metadata
- Helps clients determine if pagination should continue

### 6.5 Performance Optimization
- Apply LIMIT/OFFSET at SQL level
- Calculate count efficiently
- Only fetch data for current page
- Avoid loading all data into memory

---

## 7. DATA VALIDATION

### 7.1 Form Data Validation

**Required Structure:**
- form_data must be non-empty dictionary
- form_data must be dictionary type
- Applied on create
- On update: form_data can be empty dictionary if provided

**Validation Rules:**
- form_data cannot be empty on create
- form_data must be dictionary type
- No specific structure required (form-specific field names and values)

### 7.2 Name Validation
- Required on create
- Optional on update
- Length: 1-255 characters
- Duplicate check: Same name for same user, same form_key, and tenant not allowed
- Same name allowed for different form_keys

### 7.3 Description Validation
- Optional field
- Maximum length: 1000 characters
- Can be NULL or empty string

### 7.4 Form Key Validation
- Required on create
- Length: 1-255 characters
- Cannot be updated (form_key is immutable)
- References Camunda form definition

### 7.5 Form ID and Version Validation
- Optional fields
- form_id: Maximum length 64 characters
- form_version: Integer
- Used for version-specific templates

### 7.6 Tags Validation
- Optional field
- Maximum 20 tags per template
- Each tag maximum 50 characters
- Stored as JSONB array
- Applied on create and update (if tags provided)

### 7.7 Category Validation
- Optional field
- Maximum length: 100 characters
- Can be NULL

### 7.8 Tenant ID Validation
- Optional field
- Maximum length: 64 characters
- Can be NULL

---

## 8. SCHEMA STRUCTURES

### 8.1 FormTemplateCreate Schema
**Purpose:** Request schema for creating a new template

**Fields:**
- name: string (required, 1-255 chars)
- description: string (optional, max 1000 chars)
- form_key: string (required, 1-255 chars)
- form_id: string (optional, max 64 chars)
- form_version: integer (optional)
- form_data: dict (required, non-empty)
- is_public: boolean (default: false)
- category: string (optional, max 100 chars)
- tags: list[string] (optional, max 20 tags, each max 50 chars)
- tenant_id: string (optional, max 64 chars)

**Validation:**
- form_data must be non-empty dictionary
- tags must meet length and count constraints

### 8.2 FormTemplateUpdate Schema
**Purpose:** Request schema for updating an existing template

**Fields:**
- name: string (optional, 1-255 chars)
- description: string (optional, max 1000 chars)
- form_data: dict (optional, can be empty)
- is_public: boolean (optional)
- category: string (optional, max 100 chars)
- tags: list[string] (optional, max 20 tags, each max 50 chars)

**Validation:**
- All fields optional (partial update)
- form_key, form_id, form_version cannot be updated (immutable)
- If form_data provided, must be dictionary (can be empty)
- If tags provided, must meet constraints

### 8.3 FormTemplateResponse Schema
**Purpose:** Response schema for template data

**Fields:**
- id: string (template ID in Camunda format)
- name: string (template name)
- description: string or null (template description)
- form_key: string (Camunda form key)
- form_id: string or null (Camunda form ID)
- form_version: integer or null (Camunda form version)
- created_by: string (creator username)
- modified_by: string or null (last modifier username)
- form_data: dict (form field values)
- is_public: boolean (sharing flag)
- category: string or null (category name)
- tags: list[string] or null (tag array)
- usage_count: integer (usage counter)
- last_used_at: datetime or null (last execution timestamp)
- created_at: datetime (creation timestamp)
- updated_at: datetime (last update timestamp)
- modified_at: datetime or null (last modification timestamp)
- tenant_id: string or null (tenant identifier)

### 8.4 FormTemplateListResponse Schema
**Purpose:** Response schema for paginated template list

**Fields:**
- templates: list[FormTemplateResponse] (array of templates)
- total_count: integer (total matching templates)
- limit: integer (page size)
- offset: integer (number skipped)
- has_more: boolean (more results available)

### 8.5 FormTemplateStatsResponse Schema
**Purpose:** Response schema for template statistics

**Fields:**
- total_templates: integer (total visible templates)
- public_templates: integer (count of public templates)
- private_templates: integer (count of private templates)
- total_usage: integer (sum of usage_count)
- most_used_templates: list[FormTemplateResponse] (top 5 by usage)
- recent_templates: list[FormTemplateResponse] (top 5 by created_at)
- categories: list[dict] (category name and count pairs)
- forms: list[dict] (form_key and count pairs)

---

## 9. USAGE TRACKING

### 9.1 Usage Counter
- Incremented each time template is used
- Stored in usage_count_ field
- Atomic increment prevents race conditions
- Used for statistics and popularity tracking

### 9.2 Last Used Timestamp
- Updated each time template is used
- Stored in last_used_at_ field
- Set to current UTC timestamp
- Used for recent usage tracking

### 9.3 Atomic Updates
- Usage tracking uses database-level atomic updates
- Prevents race conditions in concurrent usage scenarios
- Updates usage_count_, last_used_at_, and rev_ in single operation
- No need to reload template after update

### 9.4 Statistics Usage
- usage_count_ used for "most used templates" statistics
- last_used_at_ used for "recently used" tracking
- total_usage sums all usage_count_ values
- Statistics respect visibility and tenant filters

---

## 10. SOFT DELETE

### 10.1 Soft Delete Mechanism
- Templates are soft-deleted by default (is_deleted_ = true)
- Soft-deleted templates remain in database
- Soft-deleted templates are excluded from all queries
- deleted_at_ timestamp records when deletion occurred
- rev_ incremented on soft delete

### 10.2 Hard Delete Option
- Hard delete permanently removes template from database
- Triggered by hard_delete=true query parameter
- Irreversible operation
- Use with caution

### 10.3 Soft Delete Behavior
- Soft-deleted templates are invisible to all queries
- All list, get, stats queries exclude soft-deleted templates
- Soft delete preserves data for potential recovery
- Hard delete removes data permanently

### 10.4 Recovery Considerations
- Soft-deleted templates can be recovered by setting is_deleted_ = false
- Hard-deleted templates cannot be recovered
- Consider retention policies for soft-deleted templates

---

## 11. MULTI-TENANCY

### 11.1 Tenant Isolation
- Templates can be associated with tenant_id_
- Users only see templates from their tenant
- Tenant filtering applied automatically based on user context
- Templates with NULL tenant_id_ visible to users with NULL tenant_id_

### 11.2 Tenant Filtering Logic
- If user has tenant_id: Show templates with matching tenant_id_
- If user has no tenant_id: Show templates with NULL tenant_id_
- Applied to all queries (list, get, stats)
- Ensures complete data isolation between tenants

### 11.3 Duplicate Check with Tenants
- Duplicate name check considers tenant_id_ and form_key_
- Same name allowed for different tenants
- Same name allowed for different form_keys
- Same name not allowed for same user, same form_key, and same tenant
- Prevents naming conflicts within tenant and form boundaries

---

## 12. REVISION TRACKING

### 12.1 Optimistic Locking
- Templates use revision numbers (rev_) for optimistic locking
- rev_ starts at 1 on creation
- rev_ incremented on each update
- rev_ incremented on soft delete
- Prevents concurrent modification conflicts

### 12.2 Revision Increment
- Updated on: template update, soft delete, usage increment
- Atomic increment prevents race conditions
- Used for optimistic locking in concurrent scenarios

---

## 13. CAMUNDA INTEGRATION

### 13.1 Form Reference
- Templates reference Camunda form definitions
- form_key_: Required, identifies the form
- form_id_: Optional, for version-specific templates
- form_version_: Optional, for version-specific templates

### 13.2 Form Data Structure
- form_data_ contains field values for the referenced form
- Field names match form field definitions
- Values match form field types
- No validation against form schema (form-specific)

### 13.3 Multiple Templates Per Form
- Users can create multiple templates for the same form
- Different templates can have different field values
- Templates identified by name (unique per user, form, tenant)
- Useful for: Different scenarios, different default values

### 13.4 ID Format
- Template IDs follow Camunda naming convention
- Format: "form-template-{12-character-hex}"
- String-based IDs (not integers)
- Compatible with Camunda system conventions

---

## 14. ERROR HANDLING

### 14.1 Validation Errors
- Return 400 Bad Request
- Include error message describing validation failure
- Common causes: Invalid form_data structure, duplicate name, invalid tags

### 14.2 Not Found Errors
- Return 404 Not Found
- Used for: Template not found, access denied (to prevent information leakage)
- Error message: "Template with ID {id} not found"

### 14.3 Forbidden Errors
- Return 403 Forbidden
- Used for: Update/delete attempts by non-creator
- Error message describes permission issue

### 14.4 Server Errors
- Return 500 Internal Server Error
- Used for: Database errors, unexpected exceptions
- Error message: "Internal server error"
- Full error details logged server-side

### 14.5 Error Logging
- All errors are logged with context
- Logs include: Error type, template ID, user, error message
- Database errors include SQL error details
- Validation errors include field and constraint details

---

## 15. PERFORMANCE CONSIDERATIONS

### 15.1 Database Indexes
**Recommended Indexes:**
- Primary key: id_ (automatic)
- created_by_: For user-specific queries
- is_public_: For public template filtering
- form_key_: For form-specific filtering
- category_: For category filtering
- is_deleted_: For excluding soft-deleted templates
- tenant_id_: For multi-tenant filtering
- created_at_: For sorting by creation date
- usage_count_: For sorting by popularity

### 15.2 Query Optimization
- Apply filters at SQL level
- Use indexes for frequently filtered columns
- Limit result sets with pagination
- Calculate counts efficiently
- Use JSONB operators efficiently for tag filtering

### 15.3 JSONB Operations
- Tags stored as JSONB for efficient querying
- Use @> (contains) operator for tag matching
- Index JSONB columns if tag filtering is common
- Consider GIN indexes for JSONB columns

### 15.4 Pagination Best Practices
- Always use pagination for list queries
- Set reasonable default limit (50)
- Enforce maximum limit (200)
- Calculate has_more efficiently
- Avoid loading all data into memory

---

## 16. IMPLEMENTATION TASKS

### Task 1: Database Schema
1. Create act_re_form_template table with all required fields
2. Create indexes for performance
3. Set up JSONB columns for form_data_ and tags_
4. Configure soft delete fields
5. Set up multi-tenancy support
6. Set up revision tracking (rev_)

### Task 2: Model Implementation
1. Create FormTemplate model
2. Configure field types and constraints
3. Set up Camunda naming conventions
4. Configure timestamps (auto-set/update)
5. Set up soft delete logic
6. Set up revision tracking

### Task 3: Schema Validation
1. Implement FormTemplateCreate schema with validators
2. Implement FormTemplateUpdate schema with validators
3. Implement response schemas
4. Add form_data validation
5. Add tag validation logic

### Task 4: Service Layer
1. Implement ID generation (Camunda format)
2. Implement create_template with duplicate check (includes form_key)
3. Implement get_template with permission check
4. Implement update_template with ownership check and revision increment
5. Implement delete_template (soft/hard) with revision increment
6. Implement list_templates with all filters and sort normalization
7. Implement increment_usage with atomic update and revision increment
8. Implement get_template_stats (if stats endpoint exists)

### Task 5: API Endpoints
1. Implement POST /forms/templates/ (create)
2. Implement GET /forms/templates/ (list)
3. Implement GET /forms/templates/{id} (get)
4. Implement PUT /forms/templates/{id} (update)
5. Implement DELETE /forms/templates/{id} (delete)

### Task 6: Permission System
1. Implement visibility filtering
2. Implement ownership checks
3. Implement access control for operations
4. Implement information leakage prevention
5. Add multi-tenant filtering

### Task 7: Filtering and Sorting
1. Implement form_key filter
2. Implement category filter
3. Implement tags filter with JSONB
4. Implement search_term filter
5. Implement is_public filter
6. Implement created_by filter
7. Implement sort field normalization
8. Implement dynamic sorting
9. Implement pagination

### Task 8: Field Mapping
1. Implement API-to-model field name mapping
2. Handle underscore suffix in field names
3. Map response fields from model to API format
4. Handle Camunda naming conventions

### Task 9: Testing
1. Test all CRUD operations
2. Test permission scenarios
3. Test filtering combinations
4. Test pagination edge cases
5. Test validation rules
6. Test multi-tenancy isolation
7. Test usage tracking
8. Test revision tracking
9. Test duplicate check with form_key
10. Performance testing

---

## 17. SUMMARY

This documentation provides a complete business-level guide for implementing the form templates functionality. Key points to remember:

1. **CRUD Operations**: Full create, read, update, delete support with proper permissions
2. **Sharing Model**: Public/private templates with visibility rules
3. **Form Reference**: Templates reference Camunda forms (form_key, form_id, form_version)
4. **Multiple Templates**: Multiple templates per form per user supported
5. **Filtering**: Comprehensive filtering by form_key, category, tags, search term, public/private, creator
6. **Pagination**: Efficient pagination with total count and has_more flag
7. **Usage Tracking**: Atomic usage counter and last_used_at timestamp
8. **Soft Delete**: Soft delete by default with hard delete option
9. **Multi-Tenancy**: Complete tenant isolation support
10. **Revision Tracking**: Optimistic locking with revision numbers
11. **Validation**: Strict validation of form_data and field constraints
12. **Permissions**: Creator-only update/delete, public templates visible to all
13. **Sort Normalization**: Map API field names to model field names with underscores
14. **Camunda Integration**: Follows Camunda naming conventions and ID formats

Follow this documentation step-by-step to ensure a complete and correct implementation.
