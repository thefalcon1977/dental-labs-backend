# Draft BPMNs API Implementation Documentation

## Overview
This document provides a comprehensive business-level guide for implementing the draft BPMNs functionality. It covers all logic, filters, permissions, CRUD operations, and data structures without any code implementation details.

The Draft BPMNs API allows users to save, manage, and reuse draft BPMN (Business Process Model and Notation) XML definitions for Camunda processes. Users can save incomplete BPMN definitions as drafts, edit them later, and deploy when ready. The system supports duplication, search, and multi-tenancy. The create endpoint uses an upsert pattern: if a draft with the same name exists, it updates instead of creating a new one.

---

## 1. BASE DATA STRUCTURE

### 1.1 Data Source
The draft BPMNs functionality uses a single data source:

**Draft BPMNs Table (draft_bpmns)**
- Contains all saved draft BPMN XML definitions
- Stores BPMN data as TEXT (XML string)
- Includes metadata: name, creator, modifier, timestamps
- Supports multi-tenancy
- Simple structure without versioning or sharing settings
- Name has unique constraint at database level

### 1.2 Core Data Fields

**Primary Identification:**
- id: Auto-incrementing integer primary key
- name: Unique name of the draft BPMN (required, max 255 characters, unique constraint at database level)

**BPMN Content:**
- bpmn_data: BPMN XML definition stored as TEXT (required)
  - Contains: Complete BPMN XML string
  - Required field - must be non-empty string
  - Example: "<bpmn:definitions>...</bpmn:definitions>"

**Ownership:**
- created_by: Username of draft creator (required, max 100 characters)
- modified_by: Username of last modifier (optional, max 100 characters)

**Timestamps:**
- created_at: Timestamp when draft was created (auto-set on creation)
- modified_at: Timestamp when draft was last modified (auto-updated on modification)

**Multi-Tenancy:**
- tenant_id: Optional tenant identifier for multi-tenant isolation (max 64 characters)

---

## 2. ENDPOINTS

### 2.1 POST `/draft-bpmns/`
**Purpose:** Create a new draft BPMN or update existing one if name already exists (upsert pattern)

**Authentication:** Not required (based on code, but should be added for production)

**Request Body:** DraftBpmnCreate schema

**Business Logic:**
1. Validate draft BPMN data (name, bpmn_data)
2. Check if draft BPMN with same name already exists
3. If exists:
   - Update existing draft with new bpmn_data
   - Update tenant_id if provided
   - Set modified_by to created_by from request
   - Set modified_at to current timestamp
   - Return updated draft (HTTP 200)
4. If not exists:
   - Create new draft BPMN record with provided data
   - Set created_by to provided user
   - Set created_at and modified_at to current timestamp
   - Return created draft (HTTP 201)
5. Return draft BPMN with all fields

**Upsert Pattern:**
- If draft with same name exists: Update it (HTTP 200 OK)
- If draft with same name doesn't exist: Create new (HTTP 201 Created)
- Response status code indicates whether draft was created or updated
- This pattern allows idempotent creation operations

**Validation Rules:**
- name: Required, 1-255 characters, cannot be empty or whitespace only
- bpmn_data: Required, must be non-empty string (XML)
- created_by: Required, 1-100 characters
- tenant_id: Optional, max 64 characters

**Response:** 201 Created or 200 OK with DraftBpmnResponse

**Error Responses:**
- 400: Validation error or database constraint violation
- 500: Internal server error

---

### 2.2 GET `/draft-bpmns/{draft_id}`
**Purpose:** Get a specific draft BPMN by ID

**Authentication:** Not required (based on code, but should be added for production)

**Path Parameters:**
- draft_id: Integer draft BPMN ID

**Business Logic:**
1. Query draft BPMN by ID
2. If not found, return 404 error
3. Return draft BPMN data including full bpmn_data XML

**Response:** 200 OK with DraftBpmnResponse

**Error Responses:**
- 404: Draft BPMN not found
- 500: Internal server error

---

### 2.3 PUT `/draft-bpmns/{draft_id}`
**Purpose:** Update an existing draft BPMN

**Authentication:** Not required (based on code, but should be added for production)

**Path Parameters:**
- draft_id: Integer draft BPMN ID

**Request Body:** DraftBpmnUpdate schema (all fields optional except modified_by)

**Business Logic:**
1. Get draft BPMN by ID
2. If not found, return 404 error
3. If name is being updated:
   - Check if another draft with new name already exists
   - If duplicate name found, return 409 Conflict error
4. Track field changes for audit purposes
5. Update only provided fields (partial update)
6. Set modified_by to provided user
7. Set modified_at to current timestamp
8. Commit changes only if fields were actually modified
9. Return updated draft BPMN

**Update Rules:**
- Partial update: Only update fields provided in request
- modified_by is required in request body
- modified_at is always updated when modified_by is provided
- If no fields changed but modified_by provided, still update timestamps
- Change tracking: Compare old and new values for each field
- Name uniqueness: Cannot update to a name that already exists

**Duplicate Name Check:**
- If name is being updated, check for duplicate name
- Exclude current draft from duplicate check
- If duplicate found, return 409 Conflict error

**Response:** 200 OK with DraftBpmnResponse

**Error Responses:**
- 404: Draft BPMN not found
- 409: Duplicate name conflict
- 400: Validation error or database constraint violation
- 500: Internal server error

---

### 2.4 DELETE `/draft-bpmns/{draft_id}`
**Purpose:** Delete a draft BPMN

**Authentication:** Not required (based on code, but should be added for production)

**Path Parameters:**
- draft_id: Integer draft BPMN ID

**Query Parameters:**
- modified_by: Required, username of user performing deletion

**Business Logic:**
1. Get draft BPMN by ID
2. If not found, return 404 error
3. Permanently delete draft BPMN from database (hard delete)
4. Return success response

**Deletion Rules:**
- Hard delete: Permanently removes draft from database
- Irreversible operation
- No soft delete mechanism
- modified_by parameter required for audit trail (though not stored)

**Response:** 200 OK with SuccessResponse

**Error Responses:**
- 404: Draft BPMN not found
- 500: Internal server error

---

### 2.5 POST `/draft-bpmns/{draft_id}/duplicate`
**Purpose:** Create a duplicate of an existing draft BPMN

**Authentication:** Not required (based on code, but should be added for production)

**Path Parameters:**
- draft_id: Integer draft BPMN ID (original draft)

**Request Body:** DraftBpmnDuplicateRequest schema

**Business Logic:**
1. Get original draft BPMN by ID
2. If not found, return 404 error
3. Check if draft with duplicate name already exists
4. If duplicate name exists, return 409 Conflict error
5. Create new draft BPMN with:
   - New name from request
   - Same bpmn_data as original
   - New created_by from request
   - Same tenant_id as original
   - New timestamps (created_at, modified_at)
6. Return created duplicate draft BPMN

**Duplication Rules:**
- Original draft BPMN must exist
- New name must be unique (database constraint)
- bpmn_data is copied exactly from original
- tenant_id is copied from original
- New timestamps are set
- New ID is auto-generated

**Duplicate Name Check:**
- Check if draft with duplicate name already exists
- If exists, return 409 Conflict error
- Prevents duplicate name conflicts

**Response:** 201 Created with DraftBpmnResponse

**Error Responses:**
- 404: Original draft BPMN not found
- 409: Duplicate name conflict
- 400: Validation error or database constraint violation
- 500: Internal server error

---

### 2.6 GET `/draft-bpmns/`
**Purpose:** List draft BPMNs with search and pagination

**Authentication:** Not required (based on code, but should be added for production)

**Query Parameters:**
- search: Optional search term (searches in name)
- created_by: Optional filter by creator (exact match)
- tenant_id: Optional filter by tenant ID (exact match)
- page: Page number (default: 1, min: 1)
- size: Page size (default: 20, min: 1, max: 100)

**Business Logic:**
1. Start with base query for all draft BPMNs
2. Apply optional filters:
   - search: Partial match (ILIKE) on name field
   - created_by: Exact match on created_by field
   - tenant_id: Exact match on tenant_id field
3. Calculate total count of matching drafts
4. Apply sorting: Order by created_at descending (newest first)
5. Apply pagination: Calculate offset from page and size, apply LIMIT and OFFSET
6. Return paginated results with metadata

**Search Filtering:**
- Searches in draft BPMN name field only
- Uses case-insensitive partial matching (ILIKE)
- Pattern: %{search}%
- Matches if search term appears anywhere in name

**Pagination:**
- Page-based pagination (not offset-based)
- page: Page number (1-indexed)
- size: Number of items per page
- offset calculated as: (page - 1) * size
- has_next calculated as: (page * size) < total

**Sorting:**
- Default sort: created_at descending (newest first)
- Applied automatically, not configurable via API

**Response:** 200 OK with DraftBpmnListResponse

**Error Responses:**
- 500: Internal server error

---

## 3. FILTERS

### 3.1 Filter Application Rules
- All filters are applied at SQL level using WHERE clauses
- Filters are combined with AND logic (all must match)
- Filters are optional - if not provided, filter is skipped
- Filters are case-sensitive for exact matches (created_by, tenant_id)
- Filters are case-insensitive for text searches (search)

### 3.2 Search Filter
- **Parameter:** search (optional string)
- **Type:** Partial match (contains)
- **Field:** DraftBpmn.name
- **Logic:** name ILIKE %search%
- **Case Sensitivity:** Case-insensitive (ILIKE)
- **Pattern:** %{search}% (matches anywhere in field)
- **Purpose:** Search for drafts by name

### 3.3 Creator Filter
- **Parameter:** created_by (optional string)
- **Type:** Exact match
- **Field:** DraftBpmn.created_by
- **Logic:** created_by == provided_value
- **Case Sensitivity:** Case-sensitive
- **Use Case:** Filter to see only drafts created by specific user

### 3.4 Tenant Filter
- **Parameter:** tenant_id (optional string)
- **Type:** Exact match
- **Field:** DraftBpmn.tenant_id
- **Logic:** tenant_id == provided_value
- **Case Sensitivity:** Case-sensitive
- **Purpose:** Multi-tenant data isolation
- **Note:** If tenant_id is NULL in database, it won't match a provided tenant_id value

---

## 4. PERMISSIONS AND ACCESS CONTROL

### 4.1 Permission Model Overview
The draft BPMNs system currently has no explicit permission checks in the API layer. All operations are available to all users. However, the following considerations apply:

### 4.2 Current Access Model
- **No Authentication Required:** Based on code, endpoints don't require authentication
- **No Ownership Checks:** Users can access, update, and delete any draft BPMN
- **No Sharing Restrictions:** All drafts are accessible to all users
- **Multi-Tenancy:** Tenant filtering is available but not enforced automatically

### 4.3 Recommended Permission Model
For production use, consider implementing:

**Rule 1: Draft Ownership**
- Draft creator should have full access to their drafts
- Creator can view, update, and delete their own drafts
- Ownership determined by created_by field matching current user

**Rule 2: Tenant Isolation**
- Users should only see drafts from their tenant
- Tenant filtering should be automatic based on user context
- Cross-tenant access should be prevented

**Rule 3: Update Permissions**
- Only draft creator should be able to update draft
- Attempts by non-creators should return 403 (forbidden)
- Upsert pattern should check ownership before updating

**Rule 4: Delete Permissions**
- Only draft creator should be able to delete draft
- Attempts by non-creators should return 403 (forbidden)

### 4.4 Multi-Tenancy Support
- Drafts can be associated with tenant_id
- Tenant filtering is available via query parameter
- Should be enforced automatically based on user context
- Drafts with NULL tenant_id visible to users with NULL tenant_id

---

## 5. SORTING

### 5.1 Sort Configuration
- Sorting is fixed and not configurable via API
- Default sort: created_at descending (newest first)
- Applied automatically in list endpoint
- Cannot be changed via query parameters

### 5.2 Sort Implementation
- Sorting is applied at SQL level using ORDER BY
- Field: DraftBpmn.created_at
- Order: DESC (descending)
- Applied after filtering but before pagination

### 5.3 Sort Behavior
- Newest drafts appear first
- Oldest drafts appear last
- Consistent ordering across pagination
- No secondary sort field

---

## 6. PAGINATION

### 6.1 Pagination Parameters
- page: Page number (default: 1, min: 1)
- size: Page size (default: 20, min: 1, max: 100)

### 6.2 Pagination Strategy

**Page-Based Approach:**
1. **Phase 1: Filter and Count**
   - Apply all filters to draft query
   - Calculate total count of matching drafts

2. **Phase 2: Paginate**
   - Calculate offset: (page - 1) * size
   - Apply LIMIT and OFFSET to sorted results
   - Execute query to fetch paginated subset
   - Return paginated results with metadata

### 6.3 Total Count Calculation
- Calculate total count after all filters are applied
- Count all matching drafts before pagination
- Return total count with paginated results
- Used to calculate has_next flag

### 6.4 Has Next Flag
- Calculate as: (page * size) < total
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

### 7.1 Name Validation
- Required on create
- Optional on update
- Length: 1-255 characters
- Cannot be empty or whitespace only
- Trimmed (leading/trailing whitespace removed)
- Unique constraint at database level

### 7.2 BPMN Data Validation
- Required on create
- Optional on update
- Must be non-empty string
- Contains BPMN XML definition
- No XML validation performed (stores as-is)
- Can be large (TEXT field, no size limit)

### 7.3 Created By Validation
- Required on create
- Length: 1-100 characters
- Cannot be empty

### 7.4 Modified By Validation
- Required on update
- Required on delete (query parameter)
- Length: 1-100 characters
- Cannot be empty

### 7.5 Tenant ID Validation
- Optional field
- Maximum length: 64 characters
- Can be NULL

---

## 8. SCHEMA STRUCTURES

### 8.1 DraftBpmnCreate Schema
**Purpose:** Request schema for creating a new draft BPMN

**Fields:**
- name: string (required, 1-255 chars, trimmed)
- bpmn_data: string (required, BPMN XML)
- created_by: string (required, 1-100 chars)
- tenant_id: string (optional, max 64 chars)

**Validation:**
- name cannot be empty or whitespace only
- name is trimmed before validation
- bpmn_data must be non-empty string

### 8.2 DraftBpmnUpdate Schema
**Purpose:** Request schema for updating an existing draft BPMN

**Fields:**
- name: string (optional, 1-255 chars, trimmed)
- bpmn_data: string (optional, BPMN XML)
- tenant_id: string (optional, max 64 chars)
- modified_by: string (required, 1-100 chars)

**Validation:**
- All fields optional except modified_by
- If name provided, cannot be empty or whitespace only
- name is trimmed before validation
- If bpmn_data provided, must be non-empty string

### 8.3 DraftBpmnResponse Schema
**Purpose:** Response schema for draft BPMN data

**Fields:**
- id: integer (draft BPMN ID)
- name: string (draft BPMN name)
- bpmn_data: string (BPMN XML definition)
- created_by: string (creator username)
- created_at: datetime (creation timestamp)
- modified_by: string or null (last modifier username)
- modified_at: datetime (last modification timestamp)
- tenant_id: string or null (tenant identifier)

### 8.4 DraftBpmnListResponse Schema
**Purpose:** Response schema for paginated draft BPMN list

**Fields:**
- bpmns: list[DraftBpmnResponse] (array of draft BPMNs)
- total: integer (total matching drafts)
- page: integer (current page number)
- size: integer (page size)
- has_next: boolean (more pages available)

### 8.5 DraftBpmnSearchRequest Schema
**Purpose:** Request schema for searching draft BPMNs

**Fields:**
- search: string (optional, search term)
- created_by: string (optional, creator filter)
- tenant_id: string (optional, tenant filter)
- page: integer (default: 1, min: 1)
- size: integer (default: 20, min: 1, max: 100)

### 8.6 DraftBpmnDuplicateRequest Schema
**Purpose:** Request schema for duplicating a draft BPMN

**Fields:**
- name: string (required, 1-255 chars, name for duplicate)
- created_by: string (required, 1-100 chars, creator of duplicate)

**Validation:**
- name cannot be empty
- name must be unique (will fail if already exists)

### 8.7 SuccessResponse Schema
**Purpose:** Response schema for success operations

**Fields:**
- message: string (success message)
- data: dict or null (optional response data)
- timestamp: datetime (response timestamp)

---

## 9. UPSERT PATTERN

### 9.1 Upsert Purpose
- Allows idempotent creation operations
- If draft with same name exists, update it instead of creating duplicate
- Prevents duplicate name errors on repeated creation attempts
- Useful for save operations that may be called multiple times

### 9.2 Upsert Process
1. Check if draft with same name already exists
2. If exists:
   - Update existing draft with new bpmn_data
   - Update tenant_id if provided
   - Set modified_by to created_by from request
   - Set modified_at to current timestamp
   - Return updated draft (HTTP 200 OK)
3. If not exists:
   - Create new draft with provided data
   - Set created_by and timestamps
   - Return created draft (HTTP 201 Created)

### 9.3 Upsert Rules
- Name is used as the unique identifier for upsert
- If name matches existing draft, update occurs
- If name doesn't match, create occurs
- Response status code indicates operation type (201 = created, 200 = updated)
- Original created_by and created_at are preserved on update

### 9.4 Upsert Benefits
- Idempotent operations: Multiple calls with same name don't create duplicates
- Prevents duplicate name errors
- Allows save operations to be called repeatedly safely
- Clear indication of create vs update via HTTP status code

---

## 10. DUPLICATION FUNCTIONALITY

### 10.1 Duplication Purpose
- Allows users to create copies of existing draft BPMNs
- Useful for creating variations of a BPMN definition
- Preserves bpmn_data from original
- Creates new draft with new name and creator

### 10.2 Duplication Process
1. Retrieve original draft BPMN by ID
2. Check if draft with duplicate name already exists
3. If duplicate name exists, return 409 Conflict error
4. Create new draft BPMN with:
   - New name from request (must be unique)
   - Copied bpmn_data from original
   - New created_by from request
   - Copied tenant_id from original
   - New timestamps (created_at, modified_at)
5. Save new draft BPMN
6. Return created duplicate

### 10.3 Duplication Rules
- Original draft BPMN must exist
- New name must be unique (database constraint)
- bpmn_data is copied exactly from original
- tenant_id is copied from original
- New timestamps are set
- New ID is auto-generated

### 10.4 Duplicate Name Check
- Check if draft with duplicate name already exists
- If exists, return 409 Conflict error
- Prevents duplicate name conflicts
- Applied before creating duplicate

---

## 11. CHANGE TRACKING

### 11.1 Change Tracking Mechanism
- Tracks field changes during update operations
- Compares old and new values for each field
- Stores change information in changes dictionary
- Used for audit purposes (though not persisted)

### 11.2 Change Detection
- For each field in update request:
  - Get old value from existing draft
  - Compare with new value
  - If different, record in changes dictionary
- Changes dictionary format: {field: {"old": old_value, "new": new_value}}

### 11.3 Timestamp Updates
- modified_at is always updated when modified_by is provided
- Even if no fields changed, timestamps are updated
- Ensures accurate last modification tracking

---

## 12. MULTI-TENANCY

### 12.1 Tenant Isolation
- Drafts can be associated with tenant_id
- Tenant filtering available via query parameter
- Should be enforced automatically based on user context
- Drafts with NULL tenant_id visible to users with NULL tenant_id

### 12.2 Tenant Filtering Logic
- If tenant_id provided: Show drafts with matching tenant_id
- If tenant_id not provided: Show all drafts (no filtering)
- Applied to search/list queries
- Should be automatic based on authenticated user context

### 12.3 Tenant Considerations
- Tenant ID is optional (can be NULL)
- Tenant ID is copied during duplication
- Tenant ID is updated during upsert if provided
- Tenant filtering should be enforced for security
- Cross-tenant access should be prevented

---

## 13. ERROR HANDLING

### 13.1 Validation Errors
- Return 400 Bad Request
- Include error message describing validation failure
- Common causes: Invalid name, missing required fields, empty bpmn_data

### 13.2 Not Found Errors
- Return 404 Not Found
- Used for: Draft BPMN not found
- Error message: "Draft BPMN with ID {id} not found"

### 13.3 Conflict Errors
- Return 409 Conflict
- Used for: Duplicate name conflicts
- Error message describes the conflict (duplicate name)
- Applied to: Update (if new name exists), Duplicate (if duplicate name exists)

### 13.4 Server Errors
- Return 400 or 500 Internal Server Error
- Used for: Database errors, unexpected exceptions
- Error message: "Internal server error" or specific error detail
- Full error details logged server-side

### 13.5 Error Logging
- All errors are logged with context
- Logs include: Error type, draft ID, name, error message
- Database errors include SQL error details
- Validation errors include field and constraint details
- Integrity errors (constraint violations) are logged separately

---

## 14. PERFORMANCE CONSIDERATIONS

### 14.1 Database Indexes
**Recommended Indexes:**
- Primary key: id (automatic)
- name: For uniqueness and lookups (unique constraint)
- created_by: For user-specific queries
- tenant_id: For multi-tenant filtering
- created_at: For time-based sorting

### 14.2 Query Optimization
- Apply filters at SQL level
- Use indexes for frequently filtered columns
- Limit result sets with pagination
- Calculate counts efficiently
- Use ILIKE efficiently for text searches

### 14.3 BPMN Data Storage
- BPMN data stored as TEXT (no size limit)
- Can be large XML files
- Consider compression if BPMN files are very large
- Index on name for fast lookups (not on bpmn_data)

### 14.4 Pagination Best Practices
- Always use pagination for list queries
- Set reasonable default page size (20)
- Enforce maximum page size (100)
- Calculate has_next efficiently
- Avoid loading all data into memory

---

## 15. IMPLEMENTATION TASKS

### Task 1: Database Schema
1. Create draft_bpmns table with all required fields
2. Create unique constraint on name field
3. Create indexes for performance
4. Set up TEXT column for bpmn_data
5. Set up multi-tenancy support

### Task 2: Model Implementation
1. Create DraftBpmn model
2. Configure field types and constraints
3. Set up timestamps (auto-set/update)
4. Implement duplicate method
5. Implement to_dict method

### Task 3: Schema Validation
1. Implement DraftBpmnCreate schema with validators
2. Implement DraftBpmnUpdate schema with validators
3. Implement response schemas
4. Add name validation (trim, non-empty)
5. Add bpmn_data validation (non-empty string)

### Task 4: Service Layer
1. Implement create_draft_bpmn (basic create)
2. Implement create_or_update_draft_bpmn (upsert pattern)
3. Implement get_draft_bpmn_by_id
4. Implement get_draft_bpmn_by_name
5. Implement get_draft_bpmns_by_creator
6. Implement update_draft_bpmn with change tracking and duplicate name check
7. Implement delete_draft_bpmn (hard delete)
8. Implement duplicate_draft_bpmn with duplicate name check
9. Implement search_draft_bpmns with filters and pagination
10. Implement get_draft_bpmn_stats (if needed)

### Task 5: API Endpoints
1. Implement POST /draft-bpmns/ (create/update with upsert)
2. Implement GET /draft-bpmns/{id} (get)
3. Implement PUT /draft-bpmns/{id} (update)
4. Implement DELETE /draft-bpmns/{id} (delete)
5. Implement POST /draft-bpmns/{id}/duplicate (duplicate)
6. Implement GET /draft-bpmns/ (list with search)

### Task 6: Permission System (Recommended)
1. Add authentication middleware
2. Implement ownership checks
3. Implement tenant isolation
4. Add permission checks for update/delete
5. Enforce automatic tenant filtering
6. Update upsert pattern to check ownership

### Task 7: Filtering and Search
1. Implement search filter (name)
2. Implement created_by filter
3. Implement tenant_id filter
4. Implement pagination (page-based)
5. Implement sorting (created_at desc)

### Task 8: Change Tracking
1. Implement change detection logic
2. Track field changes during update
3. Update timestamps appropriately
4. Log changes for audit (if needed)

### Task 9: Error Handling
1. Handle IntegrityError (database constraints)
2. Handle ValueError (validation errors)
3. Handle duplicate name conflicts (409 Conflict)
4. Implement comprehensive error logging
5. Return appropriate HTTP status codes

### Task 10: Testing
1. Test all CRUD operations
2. Test upsert pattern (create and update scenarios)
3. Test duplicate functionality
4. Test duplicate name handling
5. Test search and filtering
6. Test pagination edge cases
7. Test validation rules
8. Test multi-tenancy isolation
9. Performance testing with large BPMN files

---

## 16. SUMMARY

This documentation provides a complete business-level guide for implementing the draft BPMNs functionality. Key points to remember:

1. **CRUD Operations**: Full create, read, update, delete support
2. **Upsert Pattern**: Create endpoint updates if name exists (idempotent)
3. **Unique Names**: Name must be unique across all drafts (database constraint)
4. **BPMN XML Storage**: Stores complete BPMN XML definitions as TEXT
5. **Duplication**: Support for duplicating drafts with new name (with duplicate check)
6. **Search**: Search by name with case-insensitive partial matching
7. **Filtering**: Filter by creator and tenant
8. **Pagination**: Page-based pagination (not offset-based)
9. **Change Tracking**: Track field changes during updates
10. **Hard Delete**: Permanent deletion (no soft delete)
11. **Multi-Tenancy**: Tenant support available but not enforced
12. **No Permissions**: Currently no access control (should be added)
13. **Simple Structure**: No versioning, sharing, or categorization
14. **Conflict Handling**: 409 Conflict for duplicate name scenarios

Follow this documentation step-by-step to ensure a complete and correct implementation.
