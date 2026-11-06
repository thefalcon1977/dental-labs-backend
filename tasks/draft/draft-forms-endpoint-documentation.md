# Draft Forms API Implementation Documentation

## Overview
This document provides a comprehensive business-level guide for implementing the draft forms functionality. It covers all logic, filters, permissions, CRUD operations, and data structures without any code implementation details.

The Draft Forms API allows users to save, manage, and reuse draft form data for Camunda processes. Users can save incomplete form submissions as drafts, edit them later, and submit when ready. The system supports duplication, search, and multi-tenancy.

---

## 1. BASE DATA STRUCTURE

### 1.1 Data Source
The draft forms functionality uses a single data source:

**Draft Forms Table (draft_forms)**
- Contains all saved draft form data
- Stores form field values as JSONB
- Includes metadata: name, creator, modifier, timestamps
- Supports multi-tenancy
- Simple structure without versioning or sharing settings

### 1.2 Core Data Fields

**Primary Identification:**
- id: Auto-incrementing integer primary key
- name: Unique name of the draft form (required, max 255 characters, unique constraint at database level)

**Form Content:**
- form_data: Form field values stored as JSONB (required)
  - Contains: field names and their values as key-value pairs
  - Required field - must be dictionary
  - Example: {"leaveType": "annual", "startDate": "2025-01-15", "duration": 5}

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

### 2.1 POST `/draft-forms/`
**Purpose:** Create a new draft form

**Authentication:** Not required (based on code, but should be added for production)

**Request Body:** DraftFormCreate schema

**Business Logic:**
1. Validate draft form data (name, form_data)
2. Check for duplicate name (must be unique across all drafts)
3. Create new draft form record with provided data
4. Set created_by to provided user
5. Set created_at and modified_at to current timestamp
6. Return created draft form with all fields

**Validation Rules:**
- name: Required, 1-255 characters, cannot be empty or whitespace only
- form_data: Required, must be dictionary
- created_by: Required, 1-100 characters
- tenant_id: Optional, max 64 characters

**Duplicate Check:**
- Check if draft form with same name already exists
- Name must be unique across all draft forms (database constraint)
- If duplicate found, return 400 error with message

**Response:** 201 Created with DraftFormResponse

**Error Responses:**
- 400: Validation error or duplicate name
- 500: Internal server error

---

### 2.2 GET `/draft-forms/{draft_id}`
**Purpose:** Get a specific draft form by ID

**Authentication:** Not required (based on code, but should be added for production)

**Path Parameters:**
- draft_id: Integer draft form ID

**Business Logic:**
1. Query draft form by ID
2. If not found, return 404 error
3. Return draft form data

**Response:** 200 OK with DraftFormResponse

**Error Responses:**
- 404: Draft form not found
- 500: Internal server error

---

### 2.3 PUT `/draft-forms/{draft_id}`
**Purpose:** Update an existing draft form

**Authentication:** Not required (based on code, but should be added for production)

**Path Parameters:**
- draft_id: Integer draft form ID

**Request Body:** DraftFormUpdate schema (all fields optional except modified_by)

**Business Logic:**
1. Get draft form by ID
2. If not found, return 404 error
3. Track field changes for audit purposes
4. Update only provided fields (partial update)
5. Set modified_by to provided user
6. Set modified_at to current timestamp
7. Commit changes only if fields were actually modified
8. Return updated draft form

**Update Rules:**
- Partial update: Only update fields provided in request
- modified_by is required in request body
- modified_at is always updated when modified_by is provided
- If no fields changed but modified_by provided, still update timestamps
- Change tracking: Compare old and new values for each field

**Response:** 200 OK with DraftFormResponse

**Error Responses:**
- 404: Draft form not found
- 400: Validation error
- 500: Internal server error

---

### 2.4 DELETE `/draft-forms/{draft_id}`
**Purpose:** Delete a draft form

**Authentication:** Not required (based on code, but should be added for production)

**Path Parameters:**
- draft_id: Integer draft form ID

**Query Parameters:**
- modified_by: Required, username of user performing deletion

**Business Logic:**
1. Get draft form by ID
2. If not found, return 404 error
3. Permanently delete draft form from database (hard delete)
4. Return success response

**Deletion Rules:**
- Hard delete: Permanently removes draft from database
- Irreversible operation
- No soft delete mechanism
- modified_by parameter required for audit trail (though not stored)

**Response:** 200 OK with SuccessResponse

**Error Responses:**
- 404: Draft form not found
- 500: Internal server error

---

### 2.5 POST `/draft-forms/{draft_id}/duplicate`
**Purpose:** Create a duplicate of an existing draft form

**Authentication:** Not required (based on code, but should be added for production)

**Path Parameters:**
- draft_id: Integer draft form ID (original draft)

**Request Body:** DraftFormDuplicateRequest schema

**Business Logic:**
1. Get original draft form by ID
2. If not found, return 404 error
3. Create new draft form with:
   - New name from request
   - Same form_data as original
   - New created_by from request
   - Same tenant_id as original
   - New timestamps (created_at, modified_at)
4. Return created duplicate draft form

**Duplication Rules:**
- Duplicate name must be unique (will fail if name already exists)
- form_data is copied from original
- tenant_id is copied from original
- New timestamps are set
- New ID is auto-generated

**Response:** 201 Created with DraftFormResponse

**Error Responses:**
- 404: Original draft form not found
- 400: Validation error or duplicate name
- 500: Internal server error

---

### 2.6 GET `/draft-forms/`
**Purpose:** List draft forms with search and pagination

**Authentication:** Not required (based on code, but should be added for production)

**Query Parameters:**
- search: Optional search term (searches in name)
- created_by: Optional filter by creator (exact match)
- tenant_id: Optional filter by tenant ID (exact match)
- page: Page number (default: 1, min: 1)
- size: Page size (default: 20, min: 1, max: 100)

**Business Logic:**
1. Start with base query for all draft forms
2. Apply optional filters:
   - search: Partial match (ILIKE) on name field
   - created_by: Exact match on created_by field
   - tenant_id: Exact match on tenant_id field
3. Calculate total count of matching drafts
4. Apply sorting: Order by created_at descending (newest first)
5. Apply pagination: Calculate offset from page and size, apply LIMIT and OFFSET
6. Return paginated results with metadata

**Search Filtering:**
- Searches in draft form name field only
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

**Response:** 200 OK with DraftFormListResponse

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
- **Field:** DraftForm.name
- **Logic:** name ILIKE %search%
- **Case Sensitivity:** Case-insensitive (ILIKE)
- **Pattern:** %{search}% (matches anywhere in field)
- **Purpose:** Search for drafts by name

### 3.3 Creator Filter
- **Parameter:** created_by (optional string)
- **Type:** Exact match
- **Field:** DraftForm.created_by
- **Logic:** created_by == provided_value
- **Case Sensitivity:** Case-sensitive
- **Use Case:** Filter to see only drafts created by specific user

### 3.4 Tenant Filter
- **Parameter:** tenant_id (optional string)
- **Type:** Exact match
- **Field:** DraftForm.tenant_id
- **Logic:** tenant_id == provided_value
- **Case Sensitivity:** Case-sensitive
- **Purpose:** Multi-tenant data isolation
- **Note:** If tenant_id is NULL in database, it won't match a provided tenant_id value

---

## 4. PERMISSIONS AND ACCESS CONTROL

### 4.1 Permission Model Overview
The draft forms system currently has no explicit permission checks in the API layer. All operations are available to all users. However, the following considerations apply:

### 4.2 Current Access Model
- **No Authentication Required:** Based on code, endpoints don't require authentication
- **No Ownership Checks:** Users can access, update, and delete any draft form
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
- Field: DraftForm.created_at
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
- size: Number of items per page (default: 20, min: 1, max: 100)

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

### 7.2 Form Data Validation
- Required on create
- Optional on update
- Must be dictionary type
- No specific structure required (form-specific field names and values)
- Can be empty dictionary

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

### 8.1 DraftFormCreate Schema
**Purpose:** Request schema for creating a new draft form

**Fields:**
- name: string (required, 1-255 chars, trimmed)
- form_data: dict (required)
- created_by: string (required, 1-100 chars)
- tenant_id: string (optional, max 64 chars)

**Validation:**
- name cannot be empty or whitespace only
- name is trimmed before validation

### 8.2 DraftFormUpdate Schema
**Purpose:** Request schema for updating an existing draft form

**Fields:**
- name: string (optional, 1-255 chars, trimmed)
- form_data: dict (optional)
- tenant_id: string (optional, max 64 chars)
- modified_by: string (required, 1-100 chars)

**Validation:**
- All fields optional except modified_by
- If name provided, cannot be empty or whitespace only
- name is trimmed before validation

### 8.3 DraftFormResponse Schema
**Purpose:** Response schema for draft form data

**Fields:**
- id: integer (draft form ID)
- name: string (draft form name)
- form_data: dict (form field values)
- created_by: string (creator username)
- created_at: datetime (creation timestamp)
- modified_by: string or null (last modifier username)
- modified_at: datetime (last modification timestamp)
- tenant_id: string or null (tenant identifier)

### 8.4 DraftFormListResponse Schema
**Purpose:** Response schema for paginated draft form list

**Fields:**
- drafts: list[DraftFormResponse] (array of draft forms)
- total: integer (total matching drafts)
- page: integer (current page number)
- size: integer (page size)
- has_next: boolean (more pages available)

### 8.5 DraftFormSearchRequest Schema
**Purpose:** Request schema for searching draft forms

**Fields:**
- search: string (optional, search term)
- created_by: string (optional, creator filter)
- tenant_id: string (optional, tenant filter)
- page: integer (default: 1, min: 1)
- size: integer (default: 20, min: 1, max: 100)

### 8.6 DraftFormDuplicateRequest Schema
**Purpose:** Request schema for duplicating a draft form

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

## 9. DUPLICATION FUNCTIONALITY

### 9.1 Duplication Purpose
- Allows users to create copies of existing draft forms
- Useful for creating variations of a draft
- Preserves form_data from original
- Creates new draft with new name and creator

### 9.2 Duplication Process
1. Retrieve original draft form by ID
2. Create new draft form with:
   - New name from request (must be unique)
   - Copied form_data from original
   - New created_by from request
   - Copied tenant_id from original
   - New timestamps (created_at, modified_at)
3. Save new draft form
4. Return created duplicate

### 9.3 Duplication Rules
- Original draft form must exist
- New name must be unique (database constraint)
- form_data is copied exactly from original
- tenant_id is copied from original
- New timestamps are set
- New ID is auto-generated

---

## 10. CHANGE TRACKING

### 10.1 Change Tracking Mechanism
- Tracks field changes during update operations
- Compares old and new values for each field
- Stores change information in changes dictionary
- Used for audit purposes (though not persisted)

### 10.2 Change Detection
- For each field in update request:
  - Get old value from existing draft
  - Compare with new value
  - If different, record in changes dictionary
- Changes dictionary format: {field: {"old": old_value, "new": new_value}}

### 10.3 Timestamp Updates
- modified_at is always updated when modified_by is provided
- Even if no fields changed, timestamps are updated
- Ensures accurate last modification tracking

---

## 11. MULTI-TENANCY

### 11.1 Tenant Isolation
- Drafts can be associated with tenant_id
- Tenant filtering available via query parameter
- Should be enforced automatically based on user context
- Drafts with NULL tenant_id visible to users with NULL tenant_id

### 11.2 Tenant Filtering Logic
- If tenant_id provided: Show drafts with matching tenant_id
- If tenant_id not provided: Show all drafts (no filtering)
- Applied to search/list queries
- Should be automatic based on authenticated user context

### 11.3 Tenant Considerations
- Tenant ID is optional (can be NULL)
- Tenant ID is copied during duplication
- Tenant filtering should be enforced for security
- Cross-tenant access should be prevented

---

## 12. ERROR HANDLING

### 12.1 Validation Errors
- Return 400 Bad Request
- Include error message describing validation failure
- Common causes: Invalid name, duplicate name, missing required fields

### 12.2 Not Found Errors
- Return 404 Not Found
- Used for: Draft form not found
- Error message: "Draft form with ID {id} not found"

### 12.3 Server Errors
- Return 500 Internal Server Error
- Used for: Database errors, unexpected exceptions
- Error message: "Internal server error" or specific error detail
- Full error details logged server-side

### 12.4 Error Logging
- All errors are logged with context
- Logs include: Error type, draft ID, error message
- Database errors include SQL error details
- Validation errors include field and constraint details

---

## 13. PERFORMANCE CONSIDERATIONS

### 13.1 Database Indexes
**Recommended Indexes:**
- Primary key: id (automatic)
- name: For uniqueness and lookups
- created_by: For user-specific queries
- tenant_id: For multi-tenant filtering
- created_at: For time-based sorting

### 13.2 Query Optimization
- Apply filters at SQL level
- Use indexes for frequently filtered columns
- Limit result sets with pagination
- Calculate counts efficiently
- Use ILIKE efficiently for text searches

### 13.3 Pagination Best Practices
- Always use pagination for list queries
- Set reasonable default page size (20)
- Enforce maximum page size (100)
- Calculate has_next efficiently
- Avoid loading all data into memory

---

## 14. IMPLEMENTATION TASKS

### Task 1: Database Schema
1. Create draft_forms table with all required fields
2. Create unique constraint on name field
3. Create indexes for performance
4. Set up JSONB column for form_data
5. Set up multi-tenancy support

### Task 2: Model Implementation
1. Create DraftForm model
2. Configure field types and constraints
3. Set up timestamps (auto-set/update)
4. Implement duplicate method
5. Implement to_dict method

### Task 3: Schema Validation
1. Implement DraftFormCreate schema with validators
2. Implement DraftFormUpdate schema with validators
3. Implement response schemas
4. Add name validation (trim, non-empty)
5. Add form_data validation

### Task 4: Service Layer
1. Implement create_draft_form with duplicate name check
2. Implement get_draft_form_by_id
3. Implement get_draft_form_by_name
4. Implement get_draft_forms_by_creator
5. Implement update_draft_form with change tracking
6. Implement delete_draft_form (hard delete)
7. Implement duplicate_draft_form
8. Implement search_draft_forms with filters and pagination
9. Implement get_draft_form_stats (if needed)

### Task 5: API Endpoints
1. Implement POST /draft-forms/ (create)
2. Implement GET /draft-forms/{id} (get)
3. Implement PUT /draft-forms/{id} (update)
4. Implement DELETE /draft-forms/{id} (delete)
5. Implement POST /draft-forms/{id}/duplicate (duplicate)
6. Implement GET /draft-forms/ (list with search)

### Task 6: Permission System (Recommended)
1. Add authentication middleware
2. Implement ownership checks
3. Implement tenant isolation
4. Add permission checks for update/delete
5. Enforce automatic tenant filtering

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

### Task 9: Testing
1. Test all CRUD operations
2. Test duplicate functionality
3. Test search and filtering
4. Test pagination edge cases
5. Test validation rules
6. Test duplicate name handling
7. Test multi-tenancy isolation
8. Performance testing

---

## 15. SUMMARY

This documentation provides a complete business-level guide for implementing the draft forms functionality. Key points to remember:

1. **CRUD Operations**: Full create, read, update, delete support
2. **Unique Names**: Name must be unique across all drafts (database constraint)
3. **Duplication**: Support for duplicating drafts with new name
4. **Search**: Search by name with case-insensitive partial matching
5. **Filtering**: Filter by creator and tenant
6. **Pagination**: Page-based pagination (not offset-based)
7. **Change Tracking**: Track field changes during updates
8. **Hard Delete**: Permanent deletion (no soft delete)
9. **Multi-Tenancy**: Tenant support available but not enforced
10. **No Permissions**: Currently no access control (should be added)
11. **Simple Structure**: No versioning, sharing, or categorization
12. **Form Data**: Stores arbitrary JSON form field values

Follow this documentation step-by-step to ensure a complete and correct implementation.
