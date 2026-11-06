# Search Templates API Implementation Documentation

## Overview
This document provides a comprehensive business-level guide for implementing the search templates functionality. It covers all logic, filters, permissions, CRUD operations, and data structures without any code implementation details.

The Search Templates API allows users to save, manage, and reuse complex search query configurations. Templates can be private (visible only to creator) or public (shared with all users), and include categorization, tagging, and usage tracking.

---

## 1. BASE DATA STRUCTURE

### 1.1 Data Source
The templates functionality uses a single data source:

**Search Templates Table (search_templates)**
- Contains all saved search query templates
- Stores complete search payloads as JSONB
- Includes metadata: name, description, category, tags, sharing settings
- Tracks usage statistics and timestamps
- Supports soft deletion and multi-tenancy

### 1.2 Core Data Fields

**Primary Identification:**
- id: Auto-incrementing integer primary key
- name: Template name (required, max 255 characters)
- description: Optional description text (max 1000 characters)

**Ownership:**
- created_by: Username of template creator (required, max 100 characters)

**Template Content:**
- template_payload: Complete search query configuration stored as JSONB
  - Contains: criteria, filters, sorting, pagination, selected columns
  - Required field - must contain valid search query structure

**Sharing and Visibility:**
- is_public: Boolean flag indicating if template is shared with all users
  - false: Private template (only visible to creator)
  - true: Public template (visible to all users)

**Categorization:**
- category: Optional category name for organizing templates (max 100 characters)
- tags: Optional array of tag strings stored as JSONB
  - Maximum 20 tags per template
  - Each tag maximum 50 characters

**Usage Tracking:**
- usage_count: Integer counter for number of times template has been executed
- last_used_at: Timestamp of most recent execution (nullable)

**Timestamps:**
- created_at: Timestamp when template was created (auto-set on creation)
- updated_at: Timestamp when template was last updated (auto-updated on modification)

**Soft Delete:**
- is_deleted: Boolean flag for soft deletion (default: false)
- deleted_at: Timestamp when template was soft deleted (nullable)

**Multi-Tenancy:**
- tenant_id: Optional tenant identifier for multi-tenant isolation (max 64 characters)

---

## 2. ENDPOINTS

### 2.1 POST `/tickets/advance-search/templates/`
**Purpose:** Create a new search template

**Authentication:** Required (JWT token)

**Request Body:** SearchTemplateCreate schema

**Business Logic:**
1. Validate template data (name, description, template_payload structure)
2. Check for duplicate template name for same user and tenant
3. Create new template record with provided data
4. Set created_by to current authenticated user
5. Initialize usage_count to 0
6. Set timestamps (created_at, updated_at)
7. Return created template with all fields

**Validation Rules:**
- Name: Required, 1-255 characters
- Description: Optional, max 1000 characters
- template_payload: Required, must be non-empty dictionary
- template_payload.criteria: Required, must be dictionary
- template_payload.criteria.operator: Required field
- template_payload.criteria.conditions: Required, must be list
- tags: Optional, max 20 tags, each max 50 characters
- category: Optional, max 100 characters
- tenant_id: Optional, max 64 characters

**Duplicate Check:**
- Check if template with same name exists for current user
- Consider tenant_id in duplicate check:
  - If tenant_id provided: Check templates with same tenant_id
  - If tenant_id not provided: Check templates with NULL tenant_id
- Only check non-deleted templates (is_deleted = false)
- If duplicate found, return 400 error

**Response:** 201 Created with SearchTemplateResponse

**Error Responses:**
- 400: Validation error or duplicate name
- 500: Internal server error

---

### 2.2 GET `/tickets/advance-search/templates/`
**Purpose:** List search templates with filtering and pagination

**Authentication:** Required (JWT token)

**Query Parameters:**
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
1. Start with base query filtering out soft-deleted templates (is_deleted = false)
2. Apply tenant filtering if tenant_id provided
3. Apply visibility filtering based on current user:
   - If user authenticated: Show templates where (is_public = true OR created_by = user)
   - If no user: Show only public templates (is_public = true)
4. Apply optional filters:
   - category: Exact match on category field
   - tags: Match any of provided tags using JSONB contains operator
   - search_term: Partial match (ILIKE) on name or description
   - is_public: Exact match on is_public field
   - created_by: Exact match on created_by field
5. Calculate total count of matching templates
6. Apply sorting by specified field and order
7. Apply pagination (limit and offset)
8. Return paginated results with metadata

**Visibility Rules:**
- Users see their own templates (created_by = user) plus all public templates
- Public templates are visible to all authenticated users
- Private templates are only visible to their creator
- If no user authenticated, only public templates are shown

**Tag Filtering:**
- Tags parameter is comma-separated string (e.g., "leave,approval")
- Split into list of individual tags
- Match if template contains ANY of the provided tags
- Uses PostgreSQL JSONB @> (contains) operator
- Only matches templates where tags field is not NULL
- Case-sensitive tag matching

**Search Term Filtering:**
- Searches in template name and description fields
- Uses case-insensitive partial matching (ILIKE)
- Pattern: %{search_term}%
- Matches if search term appears anywhere in name OR description

**Sorting:**
- Default sort: created_at descending (newest first)
- Supported sort fields: Any field on SearchTemplate model
- Common fields: created_at, updated_at, name, usage_count
- Sort order: "asc" or "desc" (case-insensitive)

**Response:** 200 OK with SearchTemplateListResponse

**Error Responses:**
- 500: Internal server error

---

### 2.3 GET `/tickets/advance-search/templates/stats`
**Purpose:** Get template usage statistics and insights

**Authentication:** Required (JWT token)

**Business Logic:**
1. Start with base query filtering out soft-deleted templates
2. Apply tenant filtering if tenant_id provided
3. Apply visibility filtering (same rules as list endpoint)
4. Calculate statistics:
   - total_templates: Total count of visible templates
   - public_templates: Count of public templates
   - private_templates: Count of private templates (total - public)
   - total_usage: Sum of usage_count across all visible templates
   - most_used_templates: Top 5 templates by usage_count (descending)
   - recent_templates: Top 5 templates by created_at (descending)
   - categories: Group by category with counts (only non-null categories)
5. Return statistics dictionary

**Statistics Details:**
- All statistics respect visibility rules (user's templates + public templates)
- All statistics respect tenant filtering if provided
- Most used templates: Ordered by usage_count descending, limit 5
- Recent templates: Ordered by created_at descending, limit 5
- Categories: Grouped by category field, count of templates per category
- Only includes categories that are not NULL

**Response:** 200 OK with SearchTemplateStatsResponse

**Error Responses:**
- 500: Internal server error

---

### 2.4 GET `/tickets/advance-search/templates/{template_id}`
**Purpose:** Get a specific template by ID

**Authentication:** Required (JWT token)

**Path Parameters:**
- template_id: Integer template ID

**Business Logic:**
1. Query template by ID
2. Exclude soft-deleted templates (is_deleted = false)
3. Apply tenant filtering if tenant_id provided
4. Check permissions:
   - If template is public: Allow access
   - If template is private: Only allow if created_by = current user
   - If access denied: Return 404 (not found) to prevent information leakage
5. Return template data

**Permission Rules:**
- Public templates: Accessible by all authenticated users
- Private templates: Only accessible by creator
- If user doesn't have access, return 404 (not found) instead of 403
- This prevents information leakage about template existence

**Response:** 200 OK with SearchTemplateResponse

**Error Responses:**
- 404: Template not found or access denied
- 500: Internal server error

---

### 2.5 PUT `/tickets/advance-search/templates/{template_id}`
**Purpose:** Update an existing template

**Authentication:** Required (JWT token)

**Path Parameters:**
- template_id: Integer template ID

**Request Body:** SearchTemplateUpdate schema (all fields optional)

**Business Logic:**
1. Get template by ID (with permission check)
2. Verify user is the creator (created_by = current user)
3. If name is being updated:
   - Check for duplicate name for same user and tenant
   - Only check other templates (exclude current template)
4. Update only provided fields (partial update)
5. Update updated_at timestamp
6. Return updated template

**Update Rules:**
- Only creator can update template
- Partial update: Only update fields provided in request
- If name updated: Check for duplicate name (same user, same tenant, different template)
- Duplicate check uses same logic as create (considers tenant_id)
- template_payload validation: If provided, must have valid structure
- tags validation: If provided, must meet tag constraints (max 20, each max 50 chars)

**Response:** 200 OK with SearchTemplateResponse

**Error Responses:**
- 404: Template not found
- 403: User is not the creator
- 400: Validation error or duplicate name
- 500: Internal server error

---

### 2.6 DELETE `/tickets/advance-search/templates/{template_id}`
**Purpose:** Delete a template (soft or hard delete)

**Authentication:** Required (JWT token)

**Path Parameters:**
- template_id: Integer template ID

**Query Parameters:**
- hard_delete: Boolean flag (default: false)
  - false: Soft delete (set is_deleted = true, set deleted_at timestamp)
  - true: Hard delete (permanently remove from database)

**Business Logic:**
1. Get template by ID (with permission check)
2. Verify user is the creator (created_by = current user)
3. Perform deletion:
   - If hard_delete = false: Set is_deleted = true, set deleted_at = current timestamp
   - If hard_delete = true: Permanently delete record from database
4. Commit changes
5. Return 204 No Content

**Deletion Rules:**
- Only creator can delete template
- Soft delete by default (preserves data, hides from queries)
- Hard delete permanently removes template
- Soft-deleted templates are excluded from all list/get queries
- Hard delete is irreversible

**Response:** 204 No Content

**Error Responses:**
- 404: Template not found
- 403: User is not the creator
- 500: Internal server error

---

### 2.7 POST `/tickets/advance-search/templates/{template_id}/execute`
**Purpose:** Execute a search using a saved template

**Authentication:** Required (JWT token)

**Path Parameters:**
- template_id: Integer template ID

**Business Logic:**
1. Get template by ID (with permission check)
2. Extract template_payload from template
3. Execute search using AdvanceSearchService with template payload
4. Increment template usage_count atomically
5. Update last_used_at timestamp
6. Return template metadata and search results

**Execution Flow:**
1. Retrieve template (with permission check)
2. Extract template_payload (contains full search query configuration)
3. Pass template_payload to AdvanceSearchService.search()
4. Service executes search query and returns results
5. Atomically increment usage_count (prevents race conditions)
6. Update last_used_at to current timestamp
7. Return combined response: template metadata + search results

**Usage Tracking:**
- Increment usage_count atomically (prevents race conditions)
- Update last_used_at timestamp
- Uses database-level atomic update operation
- No need to reload template after update

**Response:** 200 OK with SearchTemplateExecuteResponse

**Response Structure:**
- template: Full template metadata (SearchTemplateResponse)
- search_results: Search execution results
  - tickets: Array of ticket objects
  - total_count: Total matching tickets
  - limit: Pagination limit used
  - offset: Pagination offset used
  - has_more: Boolean indicating more results available

**Error Responses:**
- 404: Template not found
- 500: Internal server error

---

## 3. FILTERS

### 3.1 Filter Application Rules
- All filters are applied at SQL level using WHERE clauses
- Filters are combined with AND logic (all must match)
- Filters are optional - if not provided, filter is skipped
- Filters are case-sensitive for exact matches (category, created_by)
- Filters are case-insensitive for text searches (search_term)

### 3.2 Category Filter
- **Parameter:** category (optional string)
- **Type:** Exact match
- **Field:** SearchTemplate.category
- **Logic:** category == provided_value
- **Case Sensitivity:** Case-sensitive
- **NULL Handling:** Only matches templates with non-NULL category

### 3.3 Tags Filter
- **Parameter:** tags (optional comma-separated string)
- **Type:** Array contains (any match)
- **Field:** SearchTemplate.tags (JSONB array)
- **Logic:** Template tags array contains ANY of the provided tags
- **Implementation:**
  - Split comma-separated string into list
  - Use PostgreSQL JSONB @> (contains) operator
  - Check: tags @> [tag] for each provided tag
  - Match if ANY tag matches (OR logic within filter)
- **Case Sensitivity:** Case-sensitive
- **NULL Handling:** Only matches templates where tags is not NULL

### 3.4 Search Term Filter
- **Parameter:** search_term (optional string)
- **Type:** Partial match (contains)
- **Fields:** SearchTemplate.name, SearchTemplate.description
- **Logic:** name ILIKE %search_term% OR description ILIKE %search_term%
- **Case Sensitivity:** Case-insensitive (ILIKE)
- **Pattern:** %{search_term}% (matches anywhere in field)

### 3.5 Public/Private Filter
- **Parameter:** is_public (optional boolean)
- **Type:** Exact match
- **Field:** SearchTemplate.is_public
- **Logic:** is_public == provided_value
- **Values:** true (public), false (private)

### 3.6 Creator Filter
- **Parameter:** created_by (optional string)
- **Type:** Exact match
- **Field:** SearchTemplate.created_by
- **Logic:** created_by == provided_value
- **Case Sensitivity:** Case-sensitive
- **Use Case:** Filter to see only templates created by specific user

### 3.7 Tenant Filter (Implicit)
- **Parameter:** tenant_id (from authenticated user context)
- **Type:** Exact match
- **Field:** SearchTemplate.tenant_id
- **Logic:** Applied automatically based on user's tenant context
- **Behavior:**
  - If tenant_id provided: Only show templates with matching tenant_id
  - If tenant_id not provided: Only show templates with NULL tenant_id
- **Purpose:** Multi-tenant data isolation

### 3.8 Visibility Filter (Implicit)
- **Parameter:** user (from authenticated user context)
- **Type:** Complex logic
- **Logic:**
  - If user authenticated: (is_public == true OR created_by == user)
  - If no user: (is_public == true)
- **Purpose:** Ensure users only see templates they have access to

### 3.9 Soft Delete Filter (Implicit)
- **Parameter:** Always applied
- **Type:** Exact match
- **Field:** SearchTemplate.is_deleted
- **Logic:** is_deleted == false
- **Purpose:** Exclude soft-deleted templates from all queries

---

## 4. PERMISSIONS AND ACCESS CONTROL

### 4.1 Permission Model Overview
The templates system uses a simple but effective permission model based on ownership and sharing settings.

### 4.2 Permission Rules

**Rule 1: Template Ownership**
- Template creator (created_by) has full access to their templates
- Creator can view, update, and delete their own templates
- Ownership is determined by created_by field matching current user

**Rule 2: Public Templates**
- Templates with is_public = true are visible to all authenticated users
- All users can view and execute public templates
- Only creator can update or delete public templates

**Rule 3: Private Templates**
- Templates with is_public = false are only visible to creator
- Other users cannot see, access, or execute private templates
- Access attempts return 404 (not found) to prevent information leakage

**Rule 4: Update Permissions**
- Only template creator can update template
- Attempts by non-creators return 403 (forbidden)
- Update includes: name, description, template_payload, is_public, category, tags

**Rule 5: Delete Permissions**
- Only template creator can delete template
- Attempts by non-creators return 403 (forbidden)
- Creator can choose soft delete or hard delete

**Rule 6: Execute Permissions**
- Public templates: All authenticated users can execute
- Private templates: Only creator can execute
- Execution increments usage_count and updates last_used_at

### 4.3 Multi-Tenancy Support
- Templates can be associated with tenant_id
- Users only see templates from their tenant
- Tenant isolation is enforced at query level
- Templates with NULL tenant_id are visible to users with NULL tenant_id

### 4.4 Information Leakage Prevention
- Access denied scenarios return 404 (not found) instead of 403
- Prevents attackers from discovering template existence
- Applies to: get, update, delete, execute operations
- Only creator knows if template exists if it's private

---

## 5. SORTING

### 5.1 Sort Parameters
- sort_by: Field to sort by (default: "created_at")
- sort_order: "asc" or "desc" (default: "desc")

### 5.2 Supported Sort Fields
Any field on the SearchTemplate model can be used for sorting. Common fields:

**created_at**
- Sort by template creation timestamp
- Default sort field
- Useful for: Recent templates first

**updated_at**
- Sort by last update timestamp
- Useful for: Recently modified templates

**name**
- Sort alphabetically by template name
- Useful for: Alphabetical organization

**usage_count**
- Sort by number of times template has been executed
- Useful for: Most popular templates

**last_used_at**
- Sort by last execution timestamp
- Useful for: Recently used templates

### 5.3 Sorting Implementation
- Sorting is applied at SQL level using ORDER BY
- Dynamic field selection based on sort_by parameter
- Sort order: ASC or DESC based on sort_order parameter
- Applied after filtering but before pagination

### 5.4 Sort Order Handling
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

### 7.1 Template Payload Validation

**Required Structure:**
- template_payload must be non-empty dictionary
- template_payload.criteria must exist and be dictionary
- template_payload.criteria.operator must exist
- template_payload.criteria.conditions must exist and be list

**Validation Rules:**
- template_payload cannot be empty
- template_payload must be dictionary type
- criteria must be dictionary type
- conditions must be list type
- Applied on create and update (if template_payload provided)

### 7.2 Name Validation
- Required on create
- Optional on update
- Length: 1-255 characters
- Duplicate check: Same name for same user and tenant not allowed

### 7.3 Description Validation
- Optional field
- Maximum length: 1000 characters
- Can be NULL or empty string

### 7.4 Tags Validation
- Optional field
- Maximum 20 tags per template
- Each tag maximum 50 characters
- Stored as JSONB array
- Applied on create and update (if tags provided)

### 7.5 Category Validation
- Optional field
- Maximum length: 100 characters
- Can be NULL

### 7.6 Tenant ID Validation
- Optional field
- Maximum length: 64 characters
- Can be NULL

---

## 8. SCHEMA STRUCTURES

### 8.1 SearchTemplateCreate Schema
**Purpose:** Request schema for creating a new template

**Fields:**
- name: string (required, 1-255 chars)
- description: string (optional, max 1000 chars)
- template_payload: dict (required, must have criteria structure)
- is_public: boolean (default: false)
- category: string (optional, max 100 chars)
- tags: list[string] (optional, max 20 tags, each max 50 chars)
- tenant_id: string (optional, max 64 chars)

**Validation:**
- template_payload must contain criteria with operator and conditions
- tags must meet length and count constraints

### 8.2 SearchTemplateUpdate Schema
**Purpose:** Request schema for updating an existing template

**Fields:**
- name: string (optional, 1-255 chars)
- description: string (optional, max 1000 chars)
- template_payload: dict (optional, must have criteria structure if provided)
- is_public: boolean (optional)
- category: string (optional, max 100 chars)
- tags: list[string] (optional, max 20 tags, each max 50 chars)

**Validation:**
- All fields optional (partial update)
- If template_payload provided, must have valid structure
- If tags provided, must meet constraints

### 8.3 SearchTemplateResponse Schema
**Purpose:** Response schema for template data

**Fields:**
- id: integer (template ID)
- name: string (template name)
- description: string or null (template description)
- created_by: string (creator username)
- template_payload: dict (complete search payload)
- is_public: boolean (sharing flag)
- category: string or null (category name)
- tags: list[string] or null (tag array)
- usage_count: integer (usage counter)
- last_used_at: datetime or null (last execution timestamp)
- created_at: datetime (creation timestamp)
- updated_at: datetime (last update timestamp)
- tenant_id: string or null (tenant identifier)

### 8.4 SearchTemplateListResponse Schema
**Purpose:** Response schema for paginated template list

**Fields:**
- templates: list[SearchTemplateResponse] (array of templates)
- total_count: integer (total matching templates)
- limit: integer (page size)
- offset: integer (number skipped)
- has_more: boolean (more results available)

### 8.5 SearchTemplateExecuteResponse Schema
**Purpose:** Response schema for template execution

**Fields:**
- template: SearchTemplateResponse (template metadata)
- search_results: dict (search execution results)
  - tickets: array (matching tickets)
  - total_count: integer (total matching tickets)
  - limit: integer (pagination limit)
  - offset: integer (pagination offset)
  - has_more: boolean (more results available)

### 8.6 SearchTemplateStatsResponse Schema
**Purpose:** Response schema for template statistics

**Fields:**
- total_templates: integer (total visible templates)
- public_templates: integer (count of public templates)
- private_templates: integer (count of private templates)
- total_usage: integer (sum of usage_count)
- most_used_templates: list[SearchTemplateResponse] (top 5 by usage)
- recent_templates: list[SearchTemplateResponse] (top 5 by created_at)
- categories: list[dict] (category name and count pairs)

---

## 9. USAGE TRACKING

### 9.1 Usage Counter
- Incremented each time template is executed
- Stored in usage_count field
- Atomic increment prevents race conditions
- Used for statistics and popularity tracking

### 9.2 Last Used Timestamp
- Updated each time template is executed
- Stored in last_used_at field
- Set to current UTC timestamp
- Used for recent usage tracking

### 9.3 Atomic Updates
- Usage tracking uses database-level atomic updates
- Prevents race conditions in concurrent execution scenarios
- Updates usage_count and last_used_at in single operation
- No need to reload template after update

### 9.4 Statistics Usage
- usage_count used for "most used templates" statistics
- last_used_at used for "recently used" tracking
- total_usage sums all usage_count values
- Statistics respect visibility and tenant filters

---

## 10. SOFT DELETE

### 10.1 Soft Delete Mechanism
- Templates are soft-deleted by default (is_deleted = true)
- Soft-deleted templates remain in database
- Soft-deleted templates are excluded from all queries
- deleted_at timestamp records when deletion occurred

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
- Soft-deleted templates can be recovered by setting is_deleted = false
- Hard-deleted templates cannot be recovered
- Consider retention policies for soft-deleted templates

---

## 11. MULTI-TENANCY

### 11.1 Tenant Isolation
- Templates can be associated with tenant_id
- Users only see templates from their tenant
- Tenant filtering applied automatically based on user context
- Templates with NULL tenant_id visible to users with NULL tenant_id

### 11.2 Tenant Filtering Logic
- If user has tenant_id: Show templates with matching tenant_id
- If user has no tenant_id: Show templates with NULL tenant_id
- Applied to all queries (list, get, stats)
- Ensures complete data isolation between tenants

### 11.3 Duplicate Check with Tenants
- Duplicate name check considers tenant_id
- Same name allowed for different tenants
- Same name not allowed for same user and same tenant
- Prevents naming conflicts within tenant boundaries

---

## 12. ERROR HANDLING

### 12.1 Validation Errors
- Return 400 Bad Request
- Include error message describing validation failure
- Common causes: Invalid payload structure, duplicate name, invalid tags

### 12.2 Not Found Errors
- Return 404 Not Found
- Used for: Template not found, access denied (to prevent information leakage)
- Error message: "Template with ID {id} not found"

### 12.3 Forbidden Errors
- Return 403 Forbidden
- Used for: Update/delete attempts by non-creator
- Error message describes permission issue

### 12.4 Server Errors
- Return 500 Internal Server Error
- Used for: Database errors, unexpected exceptions
- Error message: "Internal server error"
- Full error details logged server-side

### 12.5 Error Logging
- All errors are logged with context
- Logs include: Error type, template ID, user, error message
- Database errors include SQL error details
- Validation errors include field and constraint details

---

## 13. PERFORMANCE CONSIDERATIONS

### 13.1 Database Indexes
**Recommended Indexes:**
- Primary key: id (automatic)
- created_by: For user-specific queries
- is_public: For public template filtering
- category: For category filtering
- is_deleted: For excluding soft-deleted templates
- tenant_id: For multi-tenant filtering
- created_at: For sorting by creation date
- usage_count: For sorting by popularity

### 13.2 Query Optimization
- Apply filters at SQL level
- Use indexes for frequently filtered columns
- Limit result sets with pagination
- Calculate counts efficiently
- Use JSONB operators efficiently for tag filtering

### 13.3 JSONB Operations
- Tags stored as JSONB for efficient querying
- Use @> (contains) operator for tag matching
- Index JSONB columns if tag filtering is common
- Consider GIN indexes for JSONB columns

### 13.4 Pagination Best Practices
- Always use pagination for list queries
- Set reasonable default limit (50)
- Enforce maximum limit (200)
- Calculate has_more efficiently
- Avoid loading all data into memory

---

## 14. IMPLEMENTATION TASKS

### Task 1: Database Schema
1. Create search_templates table with all required fields
2. Create indexes for performance
3. Set up JSONB columns for template_payload and tags
4. Configure soft delete fields
5. Set up multi-tenancy support

### Task 2: Model Implementation
1. Create SearchTemplate model
2. Configure field types and constraints
3. Set up relationships if needed
4. Configure timestamps (auto-set/update)
5. Set up soft delete logic

### Task 3: Schema Validation
1. Implement SearchTemplateCreate schema with validators
2. Implement SearchTemplateUpdate schema with validators
3. Implement response schemas
4. Add payload structure validation
5. Add tag validation logic

### Task 4: Service Layer
1. Implement create_template with duplicate check
2. Implement get_template with permission check
3. Implement update_template with ownership check
4. Implement delete_template (soft/hard)
5. Implement list_templates with all filters
6. Implement increment_usage with atomic update
7. Implement get_template_stats

### Task 5: API Endpoints
1. Implement POST /templates/ (create)
2. Implement GET /templates/ (list)
3. Implement GET /templates/stats (statistics)
4. Implement GET /templates/{id} (get)
5. Implement PUT /templates/{id} (update)
6. Implement DELETE /templates/{id} (delete)
7. Implement POST /templates/{id}/execute (execute)

### Task 6: Permission System
1. Implement visibility filtering
2. Implement ownership checks
3. Implement access control for operations
4. Implement information leakage prevention
5. Add multi-tenant filtering

### Task 7: Filtering and Sorting
1. Implement category filter
2. Implement tags filter with JSONB
3. Implement search_term filter
4. Implement is_public filter
5. Implement created_by filter
6. Implement dynamic sorting
7. Implement pagination

### Task 8: Integration
1. Integrate with AdvanceSearchService for execution
2. Set up authentication middleware
3. Configure error handling
4. Set up logging
5. Configure metrics tracking

### Task 9: Testing
1. Test all CRUD operations
2. Test permission scenarios
3. Test filtering combinations
4. Test pagination edge cases
5. Test validation rules
6. Test multi-tenancy isolation
7. Test usage tracking
8. Performance testing

---

## 15. SUMMARY

This documentation provides a complete business-level guide for implementing the search templates functionality. Key points to remember:

1. **CRUD Operations**: Full create, read, update, delete support with proper permissions
2. **Sharing Model**: Public/private templates with visibility rules
3. **Filtering**: Comprehensive filtering by category, tags, search term, public/private, creator
4. **Pagination**: Efficient pagination with total count and has_more flag
5. **Usage Tracking**: Atomic usage counter and last_used_at timestamp
6. **Soft Delete**: Soft delete by default with hard delete option
7. **Multi-Tenancy**: Complete tenant isolation support
8. **Validation**: Strict validation of template_payload structure and field constraints
9. **Permissions**: Creator-only update/delete, public templates visible to all
10. **Execute**: Template execution with automatic usage tracking

Follow this documentation step-by-step to ensure a complete and correct implementation.
