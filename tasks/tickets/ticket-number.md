# Business Keys API Implementation Documentation

## Overview
This document provides a comprehensive business-level guide for implementing the business keys functionality. It covers all logic, filters, generation algorithm, and data structures without any code implementation details.

The Business Keys API provides functionality to generate unique, sequential business keys for process instances. Business keys are unique identifiers that combine a category, timestamp, and sequential number. The system ensures uniqueness across concurrent requests, provides an audit trail, and supports querying generated keys.

---

## 1. BASE DATA STRUCTURE

### 1.1 Data Sources
The business keys functionality uses two database tables:

**Business Key Counter Table (business_key_counter)**
- Tracks the last issued sequential number per category
- One row per category
- Maintains counter state for atomic number allocation
- Fields: category (primary key), last_number, updated_at

**Issued Business Keys Table (issued_business_keys)**
- Audit trail of all generated business keys
- Records each generated key for uniqueness enforcement and audit
- Fields: business_key (primary key), category, number, created_at, issued_date

### 1.2 Business Key Format

**Standard Format:**
- Pattern: `{category}-{timestamp}-{number}`
- Example: `ticket-20241201143022123-0000001`

**Components:**
- category: Business domain identifier (e.g., "ticket", "invoice", "employee")
- timestamp: 17-digit timestamp in format YYYYMMDDHHMMSSMMM (up to milliseconds)
- number: 7-digit sequential number, zero-padded (e.g., 0000001, 0000002)

**Format Details:**
- Timestamp: UTC timezone, includes milliseconds (17 digits total)
- Number: Zero-padded to 7 digits (0000001 to 9999999)
- Separator: Hyphen (-) between components

---

## 2. ENDPOINTS

### 2.1 POST `/business-keys/generate`
**Purpose:** Generate a unique business key for a category

**Authentication:** Not required (based on code, but should be added for production)

**Request Body:** GenerateBusinessKeyRequest schema

**Business Logic:**
1. Validate category (required, non-empty, trimmed)
2. Atomically allocate next sequential number for category
3. Generate timestamp in UTC (YYYYMMDDHHMMSSMMM format, 17 digits)
4. Pad number to 7 digits with leading zeros
5. Assemble business key: category-timestamp-number
6. Insert business key into audit table (issued_business_keys)
7. Commit transaction
8. Return generated business key with metadata

**Validation Rules:**
- category: Required, cannot be empty or whitespace only
- category is trimmed (leading/trailing whitespace removed)

**Atomic Number Allocation:**
- Uses PostgreSQL UPSERT pattern
- INSERT with ON CONFLICT to atomically increment counter
- If category doesn't exist: Insert with last_number = 1
- If category exists: Increment last_number by 1
- Returns newly allocated number
- Guarantees uniqueness across concurrent requests

**Timestamp Generation:**
- Uses UTC timezone
- Format: YYYYMMDDHHMMSSMMM (17 digits)
- Includes: Year (4), Month (2), Day (2), Hour (2), Minute (2), Second (2), Milliseconds (3)
- Example: 20241201143022123 (2024-12-01 14:30:22.123 UTC)

**Number Padding:**
- Sequential number is zero-padded to 7 digits
- Format: 0000001, 0000002, ..., 0000010, ..., 0000100, ..., 9999999
- Ensures consistent key length

**Audit Trail:**
- Every generated key is recorded in issued_business_keys table
- Records: business_key, category, number, created_at
- Provides uniqueness enforcement and audit capabilities
- Inserted in same transaction as counter increment

**Response:** 200 OK with GenerateBusinessKeyResponse

**Response Fields:**
- business_key: Complete generated key (category-timestamp-number)
- category: Category used for generation
- number: Sequential number allocated
- timestamp: Timestamp component (17 digits)

**Error Responses:**
- 400: Validation error (category missing or empty)
- 500: Database error or allocation failure

---

### 2.2 GET `/business-keys`
**Purpose:** List issued business keys with filtering and pagination

**Authentication:** Not required (based on code, but should be added for production)

**Query Parameters:**
- category: Optional filter by exact category (exact match)
- business_key: Optional filter by exact business key (exact match)
- from_date: Optional ISO date-time filter (created_at >= from_date, UTC)
- to_date: Optional ISO date-time filter (created_at <= to_date, UTC)
- limit: Page size (default: 50, min: 1, max: 200)
- offset: Number of results to skip (default: 0, min: 0)

**Business Logic:**
1. Parse date parameters if provided (ISO 8601 format with timezone)
2. Build query with optional filters:
   - category: Exact match on category field
   - business_key: Exact match on business_key field
   - from_date: created_at >= from_date
   - to_date: created_at <= to_date
3. Apply sorting: Order by created_at descending (newest first)
4. Apply pagination: LIMIT and OFFSET
5. Execute query
6. Format results with ISO 8601 timestamps
7. Return paginated results

**Date Parsing:**
- Accepts ISO 8601 format with timezone
- Handles 'Z' timezone indicator (converts to +00:00)
- Parses to datetime object
- If parsing fails, return 400 validation error

**Filtering:**
- All filters are optional
- Filters combined with AND logic
- Uses COALESCE in SQL to apply filters only when provided
- Case-sensitive exact matches

**Sorting:**
- Default sort: created_at descending (newest first)
- Applied automatically, not configurable via API

**Pagination:**
- Offset-based pagination
- limit: Number of items per page
- offset: Number of items to skip
- No total count returned (only items and pagination params)

**Response:** 200 OK with IssuedBusinessKeyListResponse

**Error Responses:**
- 400: Invalid date format
- 500: Database error

---

### 2.3 GET `/business-keys/{business_key}`
**Purpose:** Get details of a specific generated business key

**Authentication:** Not required (based on code, but should be added for production)

**Path Parameters:**
- business_key: Complete business key string (e.g., "ticket-20241201143022123-0000001")

**Business Logic:**
1. Query issued_business_keys table by business_key
2. If not found, return 404 error
3. Format created_at timestamp to ISO 8601 format
4. Return business key details

**Response:** 200 OK with IssuedBusinessKeyItem

**Error Responses:**
- 404: Business key not found
- 500: Database error

---

## 3. BUSINESS KEY GENERATION ALGORITHM

### 3.1 Generation Process

**Step 1: Category Validation**
- Validate category is provided and non-empty
- Trim category (remove leading/trailing whitespace)
- Category is case-sensitive

**Step 2: Atomic Number Allocation**
- Execute atomic UPSERT on business_key_counter table
- If category doesn't exist: Insert with last_number = 1
- If category exists: Increment last_number by 1
- Return newly allocated number
- Operation is atomic (single SQL statement)

**Step 3: Timestamp Generation**
- Get current UTC datetime
- Format as: YYYYMMDDHHMMSSMMM (17 digits)
- Includes milliseconds for uniqueness
- Example: 20241201143022123

**Step 4: Number Padding**
- Pad sequential number to 7 digits with leading zeros
- Format: 0000001, 0000002, etc.
- Ensures consistent key length

**Step 5: Key Assembly**
- Concatenate: category + "-" + timestamp + "-" + padded_number
- Result: category-timestamp-number
- Example: ticket-20241201143022123-0000001

**Step 6: Audit Trail Recording**
- Insert into issued_business_keys table
- Records: business_key, category, number
- Provides uniqueness enforcement
- Creates audit trail

**Step 7: Transaction Commit**
- Commit all changes atomically
- Ensures consistency

### 3.2 Concurrency Safety

**Atomic Operations:**
- Number allocation uses PostgreSQL UPSERT
- Single SQL statement prevents race conditions
- No application-level locking required
- Multiple concurrent requests get different numbers

**Uniqueness Guarantees:**
- Sequential numbering per category ensures uniqueness
- Timestamp component adds additional uniqueness layer
- Database constraints prevent duplicates
- Primary key on business_key enforces uniqueness

**Transaction Safety:**
- All operations in same database transaction
- If transaction rolls back, counter increment is rolled back
- Prevents gaps in numbering on rollback
- Maintains consistent state

### 3.3 Number Allocation Details

**Counter Table Structure:**
- One row per category
- last_number: Last issued sequential number
- updated_at: Timestamp of last update
- Primary key on category

**Allocation Logic:**
- First request for category: Insert with last_number = 1, return 1
- Subsequent requests: Increment last_number, return new value
- Each request gets unique number
- Numbers are strictly increasing per category

**Gap Prevention:**
- Counter increment in same transaction as business key usage
- If transaction rolls back, counter increment rolls back
- Prevents gaps in numbering
- Ensures sequential numbering

---

## 4. FILTERS

### 4.1 Filter Application Rules
- All filters are applied at SQL level using WHERE clauses
- Filters are combined with AND logic (all must match)
- Filters are optional - if not provided, filter is skipped
- Filters use COALESCE to apply only when provided
- Filters are case-sensitive for exact matches

### 4.2 Category Filter
- **Parameter:** category (optional string)
- **Type:** Exact match
- **Field:** issued_business_keys.category
- **Logic:** category == provided_value
- **Case Sensitivity:** Case-sensitive
- **Use Case:** Filter keys by business category

### 4.3 Business Key Filter
- **Parameter:** business_key (optional string)
- **Type:** Exact match
- **Field:** issued_business_keys.business_key
- **Logic:** business_key == provided_value
- **Case Sensitivity:** Case-sensitive
- **Use Case:** Find specific business key

### 4.4 From Date Filter
- **Parameter:** from_date (optional ISO 8601 date-time string)
- **Type:** Greater than or equal
- **Field:** issued_business_keys.created_at
- **Logic:** created_at >= from_date
- **Timezone:** UTC
- **Format:** ISO 8601 with timezone support
- **Use Case:** Filter keys created on or after date

### 4.5 To Date Filter
- **Parameter:** to_date (optional ISO 8601 date-time string)
- **Type:** Less than or equal
- **Field:** issued_business_keys.created_at
- **Logic:** created_at <= to_date
- **Timezone:** UTC
- **Format:** ISO 8601 with timezone support
- **Use Case:** Filter keys created on or before date

---

## 5. PAGINATION

### 5.1 Pagination Parameters
- limit: Number of items per page (default: 50, min: 1, max: 200)
- offset: Number of items to skip (default: 0, min: 0)

### 5.2 Pagination Strategy

**Offset-Based Approach:**
1. **Phase 1: Filter and Sort**
   - Apply all filters to query
   - Apply sorting (created_at DESC)

2. **Phase 2: Paginate**
   - Apply LIMIT and OFFSET to sorted results
   - Execute query to fetch paginated subset
   - Return paginated results

### 5.3 Pagination Details
- No total count calculated (performance optimization)
- Only returns items for current page
- Uses LIMIT and OFFSET at SQL level
- Applied after filtering and sorting

### 5.4 Performance Optimization
- Apply LIMIT/OFFSET at SQL level
- No total count calculation (faster queries)
- Only fetch data for current page
- Avoid loading all data into memory

---

## 6. DATA VALIDATION

### 6.1 Category Validation
- Required on generate request
- Cannot be empty or whitespace only
- Trimmed before validation (leading/trailing whitespace removed)
- No length limit specified
- Case-sensitive

### 6.2 Date Validation
- Optional on list request
- Must be valid ISO 8601 format
- Supports timezone indicators (Z, +00:00, etc.)
- Converts 'Z' to '+00:00' for parsing
- If invalid format, return 400 validation error

### 6.3 Business Key Validation
- Must be exact match in get request
- Case-sensitive
- Must exist in issued_business_keys table

---

## 7. SCHEMA STRUCTURES

### 7.1 GenerateBusinessKeyRequest Schema
**Purpose:** Request schema for generating a business key

**Fields:**
- category: string (required, non-empty, trimmed)

**Validation:**
- category cannot be empty or whitespace only
- category is trimmed before validation

### 7.2 GenerateBusinessKeyResponse Schema
**Purpose:** Response schema for generated business key

**Fields:**
- business_key: string (complete generated key)
- category: string (category used)
- number: integer (sequential number allocated)
- timestamp: string (timestamp component, 17 digits)

### 7.3 IssuedBusinessKeyItem Schema
**Purpose:** Schema for a single issued business key

**Fields:**
- business_key: string (complete business key)
- category: string (category)
- number: integer (sequential number)
- created_at: string (ISO 8601 timestamp)

### 7.4 IssuedBusinessKeyListResponse Schema
**Purpose:** Response schema for paginated business key list

**Fields:**
- items: list[IssuedBusinessKeyItem] (array of business keys)
- limit: integer (page size)
- offset: integer (number skipped)

**Note:** No total count or has_more flag (performance optimization)

---

## 8. ATOMIC NUMBER ALLOCATION

### 8.1 Allocation Mechanism
- Uses PostgreSQL UPSERT (INSERT ... ON CONFLICT)
- Single SQL statement ensures atomicity
- No application-level locking required
- Guarantees unique numbers across concurrent requests

### 8.2 Allocation SQL Pattern
```
INSERT INTO business_key_counter (category, last_number)
VALUES (:category, 1)
ON CONFLICT (category)
DO UPDATE SET last_number = business_key_counter.last_number + 1,
              updated_at = now()
RETURNING last_number;
```

### 8.3 Allocation Behavior
- First request for category: Returns 1
- Second request for category: Returns 2
- Third request for category: Returns 3
- And so on...
- Each request gets unique, sequential number

### 8.4 Concurrency Handling
- Multiple concurrent requests for same category
- Each request gets different number
- No blocking or queuing
- Linear scalability

---

## 9. AUDIT TRAIL

### 9.1 Audit Purpose
- Track all generated business keys
- Provide uniqueness enforcement
- Enable querying and reporting
- Support troubleshooting and debugging

### 9.2 Audit Record Structure
- business_key: Complete generated key (primary key)
- category: Category used for generation
- number: Sequential number allocated
- created_at: Timestamp when key was generated
- issued_date: Date component (for per-day uniqueness if needed)

### 9.3 Audit Recording
- Every generated key is recorded
- Inserted in same transaction as counter increment
- Provides backstop for uniqueness
- Enables querying and filtering

### 9.4 Uniqueness Enforcement
- Primary key constraint on business_key
- Prevents duplicate keys
- Database-level enforcement
- Additional safety beyond counter

---

## 10. ERROR HANDLING

### 10.1 Validation Errors
- Return 400 Bad Request
- Include error message describing validation failure
- Common causes: Missing category, invalid date format

### 10.2 Not Found Errors
- Return 404 Not Found
- Used for: Business key not found in get request
- Error message: "Business key not found"

### 10.3 Database Errors
- Return 500 Internal Server Error
- Used for: Database connection errors, allocation failures
- Error message: "Database error" or specific error detail
- Full error details logged server-side

### 10.4 Error Logging
- All errors are logged with context
- Logs include: Error type, category, business_key, error message
- Database errors include SQL error details
- Validation errors include field and constraint details

---

## 11. METRICS AND MONITORING

### 11.1 Performance Metrics

**Request Timing:**
- Start performance timer at beginning of request
- Calculate duration at end of request
- Record duration for all requests (success and error)

**Business Event Metrics:**
- Record business event: event type, category, status, duration
- Event types:
  - "business_key_generated" (success)
  - "business_key_generation_failed" (error)
  - "business_key_request" (list)
  - "business_key_detail_retrieved" (get)
- Event category: "generate", "list"
- Status: "success" or "error"
- Duration: Request execution time
- Additional metadata: operation_type, entity_type

**Database Operation Metrics:**
- Record database operation: operation name, table name, duration, status
- Operation name: "business_key_generation", "business_key_list"
- Table name: "business_key_counter", "issued_business_keys"
- Status: "success" or "error"
- Duration: Request execution time

**HTTP Request Metrics:**
- Record HTTP request: method, endpoint, status code, duration
- Method: "POST" (generate), "GET" (list, get)
- Endpoint: "/search/business-keys/generate", "/search/business-keys", "/search/business-keys/{business_key}"
- Status code: 200 (success), 400 (validation), 404 (not found), 500 (server error)
- Duration: Request execution time

### 11.2 Error Metrics
- Record error: error type, error code, endpoint, severity
- Error type: Exception class name
- Error code: From exception or "UNKNOWN"
- Endpoint: Full endpoint path
- Severity: "high" for all errors

---

## 12. PERFORMANCE CONSIDERATIONS

### 12.1 Database Indexes
**Recommended Indexes:**
- Primary key: category on business_key_counter (automatic)
- Primary key: business_key on issued_business_keys (automatic)
- category: For filtering by category
- created_at: For time-based filtering and sorting
- issued_date: For date-based filtering (if daily reset used)

### 12.2 Query Optimization
- Use indexes for frequently filtered columns
- Apply filters at SQL level
- Use COALESCE for optional filters
- Limit result sets with pagination
- No total count calculation (performance optimization)

### 12.3 Atomic Operations
- Single SQL statement for number allocation
- No application-level locking
- Database-level atomicity
- Very fast execution

### 12.4 Pagination Best Practices
- Always use pagination for list queries
- Set reasonable default limit (50)
- Enforce maximum limit (200)
- No total count (faster queries)
- Avoid loading all data into memory

---

## 13. IMPLEMENTATION TASKS

### Task 1: Database Schema
1. Create business_key_counter table
2. Create issued_business_keys table
3. Create primary key constraints
4. Create indexes for performance
5. Set up unique constraints

### Task 2: SQL Functions
1. Create allocate_next_business_number SQL function
2. Create insert_issued_business_key SQL function
3. Create list_issued_business_keys SQL function
4. Create get_issued_business_key SQL function
5. Test SQL functions independently

### Task 3: Schema Definitions
1. Implement GenerateBusinessKeyRequest schema
2. Implement GenerateBusinessKeyResponse schema
3. Implement IssuedBusinessKeyItem schema
4. Implement IssuedBusinessKeyListResponse schema
5. Add validation rules

### Task 4: API Endpoints
1. Implement POST /business-keys/generate (generate)
2. Implement GET /business-keys (list with filters)
3. Implement GET /business-keys/{business_key} (get)

### Task 5: Business Logic
1. Implement category validation
2. Implement atomic number allocation
3. Implement timestamp generation
4. Implement number padding
5. Implement key assembly
6. Implement audit trail recording

### Task 6: Filtering and Pagination
1. Implement category filter
2. Implement business_key filter
3. Implement date range filters (from_date, to_date)
4. Implement date parsing (ISO 8601)
5. Implement pagination (offset-based)
6. Implement sorting (created_at DESC)

### Task 7: Error Handling
1. Implement validation error handling
2. Implement not found error handling
3. Implement database error handling
4. Implement error logging
5. Return appropriate HTTP status codes

### Task 8: Metrics and Monitoring
1. Implement performance timing
2. Record business event metrics
3. Record database operation metrics
4. Record HTTP request metrics
5. Record error metrics

### Task 9: Testing
1. Test business key generation
2. Test concurrent generation (multiple requests)
3. Test uniqueness enforcement
4. Test filtering combinations
5. Test pagination edge cases
6. Test date parsing and validation
7. Test error scenarios
8. Performance testing with high concurrency

---

## 14. CONCURRENCY AND UNIQUENESS

### 14.1 Concurrency Safety
- Atomic number allocation prevents race conditions
- Multiple concurrent requests get different numbers
- No application-level locking required
- Database-level atomicity ensures safety

### 14.2 Uniqueness Guarantees
- Sequential numbering per category ensures uniqueness
- Timestamp component adds additional uniqueness layer
- Database constraints prevent duplicates
- Primary key on business_key enforces uniqueness
- Unique constraint on (category, number) provides additional safety

### 14.3 Gap Prevention
- Counter increment in same transaction as audit recording
- If transaction rolls back, counter increment rolls back
- Prevents gaps in numbering
- Ensures sequential numbering

### 14.4 Transaction Safety
- All operations in same database transaction
- Atomic commit ensures consistency
- Rollback prevents partial state
- Maintains data integrity

---

## 15. BUSINESS KEY FORMAT

### 15.1 Format Structure
- Pattern: `{category}-{timestamp}-{number}`
- Separator: Hyphen (-)
- Total length: Variable (depends on category length)

### 15.2 Component Details

**Category:**
- Business domain identifier
- Examples: "ticket", "invoice", "employee", "leave"
- No length limit
- Case-sensitive

**Timestamp:**
- Format: YYYYMMDDHHMMSSMMM (17 digits)
- Components: Year (4), Month (2), Day (2), Hour (2), Minute (2), Second (2), Milliseconds (3)
- Timezone: UTC
- Example: 20241201143022123

**Number:**
- Format: 7-digit zero-padded integer
- Range: 0000001 to 9999999
- Sequential per category
- Zero-padded for consistent length

### 15.3 Example Keys
- `ticket-20241201143022123-0000001`
- `invoice-20241201143022123-0000002`
- `employee-20241201143022123-0000001`
- `leave-20241201143022123-0000001`

---

## 16. SUMMARY

This documentation provides a complete business-level guide for implementing the business keys functionality. Key points to remember:

1. **Atomic Generation**: Uses PostgreSQL UPSERT for atomic number allocation
2. **Unique Keys**: Guaranteed unique keys across all categories
3. **Concurrency Safe**: Thread-safe without application-level locking
4. **Audit Trail**: Complete trail of all generated keys
5. **Format**: category-timestamp-number (7-digit padded number)
6. **Filtering**: Support for category, business_key, and date range filters
7. **Pagination**: Offset-based pagination (no total count)
8. **Performance**: Fast database-level generation
9. **Transaction Safety**: All operations in same transaction
10. **Gap Prevention**: Rollback prevents gaps in numbering

Follow this documentation step-by-step to ensure a complete and correct implementation.
