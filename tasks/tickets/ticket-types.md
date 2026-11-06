# Process Definitions List Implementation Documentation

## Overview
This document provides a comprehensive business-level guide for implementing the process-definitions list functionality. It covers all logic, filters, permissions, sorting, and data assembly requirements without any code implementation details.

---

## 1. BASE QUERY STRUCTURE

### 1.1 Data Sources
The process definitions list uses a single primary data source:

**Process Definition Table**
- Contains all process definitions with their metadata
- Stores: process definition ID, key, name, version, category, deployment ID, resource names, suspension state, tenant ID, version tag, history TTL, startable flag
- Includes all versions of each process definition
- Provides complete metadata for process definitions

**Deployment Table (Joined)**
- Contains deployment information for process definitions
- Stores: deployment ID, deployment time
- Joined via outer join to get deployment time information
- May be NULL if deployment information is missing

### 1.2 Query Construction Strategy
- Build a single query from Process Definition table
- Apply outer join with Deployment table to enrich with deployment time
- Apply all filters to the base query
- Query handles all process definition states (active, suspended)
- Supports multiple versions of the same process definition key

### 1.3 Required Joins

**For Base Query:**
- Outer join with Deployment table on deployment_id
- Join condition: ProcessDefinition.deployment_id == Deployment.id
- Handle gracefully if deployment doesn't exist (NULL values)

### 1.4 Data Selection
Select the following fields from base queries:
- Process definition ID (id_)
- Process definition key (key_)
- Process definition name (name_)
- Process definition version (version_)
- Category (category_)
- Deployment ID (deployment_id_)
- Resource name (resource_name_)
- Diagram resource name (dgrm_resource_name_)
- Has start form flag (has_start_form_key_)
- Suspension state (suspension_state_)
- Tenant ID (tenant_id_)
- Version tag (version_tag_)
- History TTL (history_ttl_)
- Startable flag (startable_)
- Deployment time (from Deployment table, deploy_time_)

---

## 2. FILTERS

### 2.1 Filter Application Rules
- All filters are applied at SQL level using WHERE clauses
- Filters are applied to the Process Definition query
- Multiple filters are combined with AND logic
- Filters are case-insensitive where appropriate (use ILIKE for text searches)
- All filters are optional - if not provided, filter is skipped

### 2.2 Text-Based Filters

**Search Term Filter (search_term)**
- Searches across multiple fields: process definition ID, key, and name
- Uses partial match (contains) with ILIKE pattern matching
- Pattern: `%{search_term}%`
- Applied to ProcessDefinition.id_, ProcessDefinition.key_, ProcessDefinition.name_ fields
- Uses OR logic: matches if any of the three fields contain the search term
- Case-insensitive matching

### 2.3 Category Filter (category)
- Filter by process definition category
- Uses exact match (equals)
- Applied to ProcessDefinition.category_ field
- Case-sensitive matching
- If category is NULL in database, it won't match a provided category value

### 2.4 Version Tag Filter (version_tag)
- Filter by process definition version tag
- Uses exact match (equals)
- Applied to ProcessDefinition.version_tag_ field
- Case-sensitive matching
- If version_tag is NULL in database, it won't match a provided version_tag value

### 2.5 Startable Filter (startable)
- Filter by whether process definition is startable
- Boolean filter: true or false
- Applied to ProcessDefinition.startable_ field
- Exact match: startable_ == true or startable_ == false
- If startable_ is NULL in database, it won't match either true or false

### 2.6 Suspension State Filter (is_suspended)
- Filter by process definition suspension state
- Boolean filter: true (suspended) or false (active)
- Applied to ProcessDefinition.suspension_state_ field
- Mapping:
  - is_suspended = true: suspension_state_ == 2 (suspended)
  - is_suspended = false: suspension_state_ == 1 (active)
- If suspension_state_ is NULL, it won't match either condition

### 2.7 Tenant Filter (tenant_id)
- Filter by tenant ID
- Uses exact match (equals)
- Applied to ProcessDefinition.tenant_id_ field
- Case-sensitive matching
- If tenant_id is NULL in database, it won't match a provided tenant_id value

### 2.8 Version Filtering Options

**Latest Version Only Filter (latest_version_only)**
- Boolean flag: when true, only return the latest version of each process definition
- Logic:
  - For each unique process definition key, find the maximum version number
  - If tenant_id filter is provided, apply it to the version filtering subquery
  - Return only process definitions where version equals the maximum version for that key
- Uses subquery with GROUP BY and MAX aggregation
- Applied after other filters but before sorting and pagination

**Latest Active Startable Only Filter (latest_active_startable_only)**
- Boolean flag: when true, only return the latest version of each process definition that is both active and startable
- Logic:
  - For each unique process definition key, find the maximum version number
  - Only consider process definitions where:
    - suspension_state_ == 1 (active, not suspended)
    - startable_ == true (startable)
  - If tenant_id filter is provided, apply it to the version filtering subquery
  - Return only process definitions where version equals the maximum version for that key and meets the active/startable criteria
- Uses subquery with GROUP BY, MAX aggregation, and WHERE conditions
- Applied after other filters but before sorting and pagination
- Mutually exclusive with latest_version_only (only one should be true)

---

## 3. SORTING

### 3.1 Sort Parameters
- sort_by: Field to sort by (default: "version")
- sort_order: "asc" or "desc" (default: "desc")

### 3.2 Supported Sort Fields

**version**
- Sort by process definition version number
- Uses ProcessDefinition.version_ field
- Numeric comparison
- Default sort field

**created**
- Sort by deployment time (creation time)
- Uses Deployment.deploy_time_ field
- Date/time comparison
- NULL values handled with NULLS LAST
- If deployment doesn't exist, those records appear last

### 3.3 Sorting Implementation Strategy

**For Base Query:**
1. Map sort_by parameter to appropriate database column
2. Apply ORDER BY clause with selected sort field
3. Apply sort_order direction (ASC or DESC)
4. Handle NULL values consistently (NULLS LAST for both ASC and DESC)
5. Apply sorting before pagination

**Sort Field Mapping:**
- "version" → ProcessDefinition.version_
- "created" → Deployment.deploy_time_
- Invalid sort_by values are rejected with validation error

### 3.4 Sort Order Handling
- Default to "desc" if not specified
- Case-insensitive comparison ("asc", "desc", "ASC", "DESC")
- NULL values always placed last regardless of sort order
- For "created" sort: records without deployment appear last

### 3.5 Secondary Sort
- When primary sort values are equal, use process definition ID as tiebreaker
- Ensures consistent ordering across pagination
- Applied implicitly by database

---

## 4. PAGINATION

### 4.1 Pagination Parameters
- limit: Number of items per page (default: from settings, min: 1, max: from settings)
- offset: Number of items to skip (default: 0, min: 0)

### 4.2 Pagination Strategy

**Two-Phase Approach:**
1. **Phase 1: Filter, Sort, and Count**
   - Apply all filters to Process Definition query
   - Apply sorting
   - Calculate total count of matching records

2. **Phase 2: Paginate**
   - Apply LIMIT and OFFSET to sorted results
   - Execute query to fetch paginated subset
   - Return paginated results with total count

### 4.3 Total Count Calculation
- Calculate total count after all filters are applied
- Count all matching process definitions before pagination
- Return total count with paginated results
- Used to calculate has_more flag

### 4.4 Has More Flag
- Calculate as: (offset + limit) < total_count
- Indicates if more pages are available
- Returned in response metadata
- Helps clients determine if pagination should continue

### 4.5 Performance Optimization
- Apply LIMIT/OFFSET at SQL level
- Calculate count efficiently (may use COUNT(*) with same filters)
- Only fetch data for current page
- Avoid loading all data into memory

---

## 5. DATA ASSEMBLY

### 5.1 Process Definition Data Structure

**Core Fields:**
- id: Process definition ID (string)
- key: Process definition key (string)
- name: Process definition name (string, empty string if NULL)
- version: Process definition version number (integer)
- category: Category name (string, empty string if NULL)
- deployment_id: Deployment ID (string)
- resource_name: BPMN resource file name (string, empty string if NULL)
- diagram_resource_name: Process diagram resource file name (string, may be NULL)
- has_start_form: Boolean indicating if process has start form
- suspension_state: Suspension state number (1 = active, 2 = suspended)
- tenant_id: Tenant ID (string, may be NULL)
- version_tag: Version tag (string, may be NULL)
- history_ttl: History time-to-live in days (integer, may be NULL)
- startable: Boolean indicating if process is startable
- is_active: Computed boolean (suspension_state == 1)
- is_suspended: Computed boolean (suspension_state == 2)
- created: Deployment time in ISO 8601 format (string, may be NULL)
- deployment_time: Deployment time in ISO 8601 format (string, may be NULL)

### 5.2 Data Transformation Process

**Step 1: Base Data Collection**
- Fetch process definition data from query results
- Include deployment information from joined table
- Handle NULL values appropriately

**Step 2: Field Mapping**
- Map database column names to response field names
- Convert database field names (with trailing underscore) to API field names
- Example: id_ → id, key_ → key, name_ → name

**Step 3: Computed Fields**
- Calculate is_active: suspension_state_ == 1
- Calculate is_suspended: suspension_state_ == 2
- Convert has_start_form_key_ to boolean has_start_form
- Convert startable_ to boolean startable

**Step 4: Null Handling**
- Convert NULL name_ to empty string ""
- Convert NULL category_ to empty string ""
- Convert NULL resource_name_ to empty string ""
- Keep NULL for optional fields: tenant_id, version_tag, history_ttl, diagram_resource_name
- Handle NULL deployment gracefully (created and deployment_time become NULL)

**Step 5: Timestamp Formatting**
- Format deployment.deploy_time_ to ISO 8601 format
- Use .isoformat() method or equivalent
- Handle NULL deployment time (return NULL in response)
- Both created and deployment_time use same value from deployment

**Step 6: Boolean Conversion**
- Convert has_start_form_key_ to boolean:
  - If NULL → False
  - If not NULL → True (if value exists)
- Convert startable_ to boolean:
  - If NULL → False
  - If not NULL → True (if value is truthy)

### 5.3 Data Source
- All data is fetched from Process Definition table
- Deployment information from joined Deployment table
- Single source ensures consistent data representation
- No need for data source priority or deduplication

### 5.4 Null Handling
- Return empty strings "" for required string fields that are NULL (name, category, resource_name)
- Return NULL for optional fields (tenant_id, version_tag, history_ttl, diagram_resource_name, created, deployment_time)
- Return False for boolean fields that are NULL
- Handle missing deployment gracefully (NULL values)

### 5.5 Response Format
- process_definitions: Array of process definition objects
- total_count: Total number of process definitions matching filters
- limit: Requested page size
- offset: Requested offset
- has_more: Boolean indicating more pages available

---

## 6. VALIDATION AND ERROR HANDLING

### 6.1 Input Validation

**Pagination Validation:**
- Validate limit: Must be between 1 and maximum limit from settings
- Validate offset: Must be >= 0
- If validation fails, return 400 error with VALIDATION_INVALID_INPUT code

**Sorting Validation:**
- Validate sort_by: Must be "version" or "created"
- If invalid, return 400 error with VALIDATION_INVALID_INPUT code
- Validate sort_order: Must be "asc" or "desc" (case-insensitive)
- If invalid, use default "desc"

**Filter Validation:**
- All filter parameters are optional
- No validation needed for optional filters
- Empty strings are treated as no filter (skip filter)

### 6.2 Database Error Handling
- Handle connection errors gracefully
- Handle query timeout errors
- Handle missing table errors gracefully
- Log all database errors with context
- Return appropriate HTTP status codes (500 for database errors)

**Error Types:**
- SQLAlchemyError: Database-specific errors
  - Log error with details
  - Record error metrics
  - Return 500 with "Database error occurred" message
- General Exception: Unexpected errors
  - Log error with details
  - Record error metrics
  - Return 500 with "Internal server error" message

### 6.3 Missing Data Handling
- Handle missing deployment information gracefully (NULL values)
- Handle missing optional fields gracefully (NULL in response)
- Return partial data when non-critical data is missing
- Don't fail entire request if optional data is missing

### 6.4 Authentication Errors
- Authentication is currently disabled (TEMPORARILY DISABLED)
- When enabled, require JWT authentication for all requests
- Return 401 if authentication fails
- Extract user information from JWT token when enabled

---

## 7. METRICS AND MONITORING

### 7.1 Performance Metrics

**Request Timing:**
- Start performance timer at beginning of request
- Calculate duration at end of request
- Record duration for all requests (success and error)

**Database Operation Metrics:**
- Record database operation: operation name, table name, duration, status
- Operation name: "process_definition_list"
- Table name: "process_definition"
- Status: "success" or "error"
- Duration: Request execution time

**Business Event Metrics:**
- Record business event: event type, category, status, duration
- Event type: "process_definitions_listed"
- Event category: "list"
- Status: "success" or "error"
- Duration: Request execution time
- Additional metadata: operation_type, entity_type

**HTTP Request Metrics:**
- Record HTTP request: method, endpoint, status code, duration
- Method: "GET"
- Endpoint: "/workflow-engine/process-definitions/"
- Status code: 200 (success), 400 (validation error), 500 (server error)
- Duration: Request execution time

### 7.2 Error Metrics

**Error Recording:**
- Record error: error type, error code, endpoint, severity
- Error type: "SQLAlchemyError" or "Exception"
- Error code: "DATABASE_ERROR" or "INTERNAL_SERVER_ERROR"
- Endpoint: "/workflow-engine/process-definitions/"
- Severity: "high" for all errors

### 7.3 Monitoring Considerations
- Track query execution times
- Monitor database query counts
- Track pagination usage patterns
- Monitor filter usage (which filters are used most)
- Log slow queries for optimization
- Track error rates

---

## 8. PERFORMANCE CONSIDERATIONS

### 8.1 Query Optimization
- Use appropriate indexes on frequently filtered columns
- Apply filters at SQL level, not in application code
- Use efficient joins (outer join for deployment)
- Optimize subqueries for version filtering

### 8.2 Indexing Requirements
**Critical Indexes:**
- Process definition ID (primary key)
- Process definition key (for version filtering)
- Process definition version (for sorting and version filtering)
- Category (for category filter)
- Version tag (for version_tag filter)
- Tenant ID (for tenant_id filter)
- Suspension state (for is_suspended filter)
- Startable flag (for startable filter)
- Deployment ID (for join with Deployment table)
- Deployment time (for sorting by created)

**Composite Indexes:**
- (key_, version_) for version filtering queries
- (key_, suspension_state_, startable_, version_) for latest_active_startable_only filter
- (tenant_id_, key_, version_) if tenant filtering is common

### 8.3 Query Execution Strategy
- Execute query with optimized execution plan
- Use connection pooling for database connections
- Apply LIMIT/OFFSET at SQL level
- Calculate count efficiently (may reuse filtered query)
- Only fetch required columns

### 8.4 Caching Considerations
- Cache process definition metadata (changes infrequently)
- Consider caching deployment information
- Don't cache filtered/sorted results (too dynamic)
- Cache total counts with short TTL if acceptable
- Invalidate cache on process definition updates

### 8.5 Performance Monitoring
- Track query execution times
- Monitor database query counts
- Track pagination buffer sizes
- Monitor memory usage
- Log slow queries for optimization
- Track filter combinations that are slow

---

## 9. IMPLEMENTATION TASKS

### Task 1: Base Query Construction
1. Create Process Definition query with required joins (Deployment)
2. Handle missing deployment gracefully (outer join)
3. Ensure query handles all process definition states (active, suspended)
4. Support multiple versions of the same process definition key

### Task 2: Filter Implementation
1. Implement text-based search filter (search_term) with OR logic across id, key, name
2. Implement category filter with exact match
3. Implement version_tag filter with exact match
4. Implement startable filter with boolean matching
5. Implement is_suspended filter with state mapping (1=active, 2=suspended)
6. Implement tenant_id filter with exact match
7. Implement latest_version_only filter with subquery
8. Implement latest_active_startable_only filter with subquery and conditions

### Task 3: Sorting Implementation
1. Map sort fields to database columns (version, created)
2. Implement sorting for query results
3. Handle NULL values consistently (NULLS LAST)
4. Support both ASC and DESC sort orders
5. Validate sort_by parameter

### Task 4: Pagination System
1. Validate limit and offset parameters
2. Calculate total count after filters
3. Apply LIMIT/OFFSET at SQL level
4. Calculate has_more flag
5. Return paginated results with metadata

### Task 5: Data Assembly
1. Map database fields to response fields
2. Calculate computed fields (is_active, is_suspended)
3. Convert boolean fields appropriately
4. Handle NULL values (empty strings for required fields, NULL for optional)
5. Format timestamps to ISO 8601
6. Construct response structure

### Task 6: Validation and Error Handling
1. Implement input validation (limit, offset, sort_by)
2. Handle database errors gracefully
3. Handle missing data gracefully
4. Implement error logging
5. Return appropriate HTTP status codes

### Task 7: Metrics and Monitoring
1. Implement performance timing
2. Record database operation metrics
3. Record business event metrics
4. Record HTTP request metrics
5. Record error metrics
6. Add performance monitoring hooks

### Task 8: Performance Optimization
1. Create required database indexes
2. Optimize query execution plans
3. Implement query result optimization
4. Add performance monitoring
5. Optimize version filtering subqueries

### Task 9: Testing
1. Test all filter combinations
2. Test version filtering options (latest_version_only, latest_active_startable_only)
3. Test sorting with all fields and orders
4. Test pagination edge cases (first page, last page, empty results)
5. Test error scenarios
6. Performance testing with large datasets
7. Test NULL value handling
8. Test missing deployment handling

---

## 10. DESIGN PATTERNS RECOMMENDATIONS

### 10.1 Overview
To implement the process-definitions list functionality effectively, several design patterns are recommended to ensure maintainability, testability, and scalability.

### 10.2 Pattern Priority Classification

**MUST HAVE (Critical for Core Functionality):**
- Repository Pattern
- Specification Pattern
- Builder Pattern

**SHOULD HAVE (Important for Flexibility):**
- Strategy Pattern
- Template Method Pattern

**NICE TO HAVE (Enhancement Opportunities):**
- Factory Pattern
- Value Object Pattern

### 10.3 Recommended Patterns

#### 10.3.1 Repository Pattern (MUST HAVE)

**Purpose:** Abstract data access layer and provide clean interface for process definition operations.

**Why Essential:**
- Complex queries should be encapsulated
- Easier testing with mock repositories
- Separation of concerns (business logic vs data access)
- Handles joins and subqueries cleanly

**Implementation Guidance:**
- Create `IProcessDefinitionRepository` interface
- Implement `ProcessDefinitionRepository` with methods:
  - `findProcessDefinitions(criteria, sorting, pagination)`
  - `countProcessDefinitions(criteria)`
- Repository handles all SQL query construction
- Service layer uses repository, not direct database access

**Benefits:**
- Abstraction: Business logic doesn't depend on database structure
- Testable: Easy to create mock repositories
- Maintainable: Database changes isolated to repository
- Reusable: Repository can be used by multiple services

#### 10.3.2 Specification Pattern (MUST HAVE)

**Purpose:** Build complex filter criteria dynamically and composably.

**Why Essential:**
- Multiple filter types need to be combined flexibly
- Filters must work with AND logic
- Each filter should be independently testable
- Easy to add new filters without modifying existing code

**Implementation Guidance:**
- Create base `ISpecification` interface with `is_satisfied_by()` method
- Implement individual specifications:
  - `SearchTermSpecification`
  - `CategorySpecification`
  - `VersionTagSpecification`
  - `StartableSpecification`
  - `SuspensionStateSpecification`
  - `TenantIdSpecification`
  - `LatestVersionOnlySpecification`
  - `LatestActiveStartableOnlySpecification`
- Create composite specifications: `AndSpecification`
- Apply specifications to query
- Each specification encapsulates SQL WHERE clause logic

**Benefits:**
- Composable: Combine filters easily
- Testable: Each specification can be unit tested independently
- Maintainable: New filters don't affect existing ones
- Reusable: Specifications work consistently

#### 10.3.3 Builder Pattern (MUST HAVE)

**Purpose:** Construct complex queries step by step with a fluent, readable API.

**Why Essential:**
- Many optional parameters (filters, sorting, pagination)
- Complex query construction needs clear structure
- Improves code readability and maintainability
- Handles version filtering subqueries cleanly

**Implementation Guidance:**
- Create `ProcessDefinitionQueryBuilder` class
- Methods: `withFilter()`, `withSorting()`, `withPagination()`, `withVersionFiltering()`
- Final `build()` method returns executable query
- Support method chaining for fluent API

**Example Structure:**
```
ProcessDefinitionQueryBuilder
  .withFilter(searchTermSpecification)
  .withFilter(categorySpecification)
  .withVersionFiltering(latestVersionOnly)
  .withSorting(sortBy, sortOrder)
  .withPagination(limit, offset)
  .build()
```

**Benefits:**
- Readable: Clear intent of query construction
- Flexible: Easy to add new builder methods
- Type-safe: Compile-time checking of query structure
- Testable: Can mock builders for testing

#### 10.3.4 Strategy Pattern (SHOULD HAVE)

**Purpose:** Encapsulate different algorithms for sorting and version filtering.

**Why Important:**
- Multiple sort fields with different implementations
- Different version filtering strategies
- Easy to add new strategies without modifying existing code

**Implementation Guidance:**
- Create `SortStrategy` interface with `apply_sort(query, order)` method
- Implement strategies: `VersionSortStrategy`, `CreatedSortStrategy`
- Create `VersionFilterStrategy` interface for version filtering
- Implement strategies: `LatestVersionOnlyStrategy`, `LatestActiveStartableOnlyStrategy`, `NoVersionFilterStrategy`
- Use factory or registry to select appropriate strategy

**Benefits:**
- Extensible: Add new strategies without changing existing code
- Testable: Each strategy independently testable
- Flexible: Can swap strategies at runtime
- Maintainable: Strategy logic isolated and focused

#### 10.3.5 Template Method Pattern (SHOULD HAVE)

**Purpose:** Define the skeleton of the process definition listing algorithm.

**Why Important:**
- Consistent execution flow for process definition listing
- Ensures correct order of operations (filter → sort → paginate)
- Allows customization of specific steps while maintaining overall structure

**Implementation Guidance:**
- Create `ProcessDefinitionListService` base class with template method `listProcessDefinitions()`
- Define steps: `buildQuery()`, `applyFilters()`, `applyVersionFiltering()`, `applySorting()`, `applyPagination()`, `transformData()`
- Subclasses can override specific steps if needed
- Template method ensures correct execution order

**Benefits:**
- Consistency: Same flow for all process definition listing operations
- Maintainability: Changes to flow happen in one place
- Flexibility: Override specific steps when needed
- Clear structure: Easy to understand execution flow

#### 10.3.6 Factory Pattern (NICE TO HAVE)

**Purpose:** Create appropriate query builders, repositories, or strategies based on context.

**Why Useful:**
- Centralized object creation logic
- Consistent builder creation patterns
- Easy to extend with new builder types if needed

**Implementation Guidance:**
- Create `QueryBuilderFactory` to create query builders
- Create `FilterStrategyFactory` to create appropriate filter strategies
- Create `SortStrategyFactory` to create appropriate sort strategies
- Factories encapsulate creation logic and dependencies

**Benefits:**
- Centralized: Creation logic in one place
- Flexible: Easy to add new types
- Testable: Can mock factories
- Maintainable: Changes to creation logic isolated

#### 10.3.7 Value Object Pattern (NICE TO HAVE)

**Purpose:** Represent filters, sorting, and pagination as immutable value objects.

**Why Useful:**
- Ensures type safety and prevents invalid states
- Makes API cleaner and easier to extend
- Encapsulates validation logic

**Implementation Guidance:**
- Create `FilterCriteria` value object
- Create `SortCriteria` value object
- Create `PaginationCriteria` value object
- Create `ProcessDefinitionQuery` object that encapsulates all parameters
- Value objects are immutable and validate themselves

**Benefits:**
- Type-safe: Compile-time checking
- Immutable: Prevents accidental modification
- Validated: Invalid states cannot be created
- Clean API: Single object instead of many parameters

### 10.4 Recommended Architecture

```
┌─────────────────────────────────────────────────┐
│    ProcessDefinitionListService                  │
│    (Template Method - Orchestrator)              │
│  - listProcessDefinitions(criteria, etc.)        │
└──────────────┬──────────────────────────────────┘
               │
       ┌───────┴──────────────┐
       │                      │
┌──────▼──────────┐  ┌────────▼────────────┐
│  Repository     │  │  Specification       │
│   Pattern       │  │   Pattern            │
│                 │  │                      │
│ IProcessDefRepo │  │ ISpecification       │
│  - find()      │  │  - is_satisfied_by() │
│  - count()     │  │                      │
└──────┬──────────┘  └────────┬────────────┘
       │                      │
┌──────▼──────────────────────▼────────────┐
│      QueryBuilder (Builder Pattern)     │
│  - ProcessDefinitionQueryBuilder        │
│  - withFilter(specification)            │
│  - withSorting(strategy)                │
│  - withPagination(limit, offset)        │
│  - withVersionFiltering(strategy)       │
└──────┬───────────────────────────────────┘
       │
┌──────▼───────────────────────────────────┐
│   Filter/Sort Strategies (Strategy)      │
│  - SearchTermFilterStrategy              │
│  - CategoryFilterStrategy                │
│  - VersionSortStrategy                   │
│  - CreatedSortStrategy                   │
│  - LatestVersionOnlyStrategy             │
│  - LatestActiveStartableOnlyStrategy     │
└──────────────────────────────────────────┘
```

### 10.5 Implementation Priority

**Phase 1: Core Patterns (Start Here)**
1. Repository Pattern - Establish data access abstraction
2. Specification Pattern - Implement core filtering logic
3. Builder Pattern - Build query construction system

**Phase 2: Enhancement Patterns**
4. Strategy Pattern - Add sorting and version filtering variations
5. Template Method Pattern - Define execution flow

**Phase 3: Optimization Patterns**
6. Factory Pattern - Centralize object creation
7. Value Object Pattern - Improve type safety

### 10.6 Pattern Benefits Summary

**Maintainability:**
- Easy to add new filters without modifying existing code
- Clear separation of concerns
- Changes isolated to specific components

**Testability:**
- Each component can be unit tested independently
- Easy to create mocks for testing
- Test filters, sorting, and version filtering separately

**Performance:**
- Optimize individual components
- Query optimization isolated to repository
- Efficient version filtering strategies

**Flexibility:**
- Swap implementations without affecting other parts
- Add new features by adding new strategies/specifications
- Support different filter and sort combinations

**Scalability:**
- Patterns support growth in filter types
- Easy to extend with new version filtering options
- Patterns handle complexity gracefully

---

## 11. IMPORTANT NOTES AND TIPS

### 11.1 Version Management
- Process definitions can have multiple versions with the same key
- Version filtering options (latest_version_only, latest_active_startable_only) help manage this
- Always consider version when filtering or sorting
- Latest version is determined by maximum version number per key

### 11.2 Suspension State Handling
- Suspension state values: 1 = active, 2 = suspended
- is_active and is_suspended are computed fields for convenience
- Always use suspension_state_ for filtering, compute is_active/is_suspended for response

### 11.3 Deployment Information
- Deployment information is optional (outer join)
- Handle NULL deployment gracefully
- created and deployment_time are the same value (from deployment)
- If deployment doesn't exist, both fields are NULL

### 11.4 Boolean Field Handling
- has_start_form_key_ is converted to boolean has_start_form
- If NULL → False, if not NULL → True
- startable_ is converted to boolean startable
- If NULL → False, if not NULL → True (if value is truthy)

### 11.5 Null Value Handling
- Required string fields (name, category, resource_name): NULL → empty string ""
- Optional fields (tenant_id, version_tag, history_ttl, diagram_resource_name): NULL → NULL
- Boolean fields: NULL → False
- Timestamp fields: NULL → NULL

### 11.6 Version Filtering Logic
- latest_version_only and latest_active_startable_only are mutually exclusive
- Both use subqueries with GROUP BY and MAX aggregation
- Tenant filter is applied to version filtering subquery if provided
- Version filtering happens after other filters but before sorting

### 11.7 Search Term Logic
- Search term uses OR logic across three fields: id, key, name
- Case-insensitive partial matching
- Pattern: %{search_term}%
- Applied to all three fields simultaneously

### 11.8 Performance Tips
- Use indexes on all filtered and sorted columns
- Optimize version filtering subqueries
- Apply filters at SQL level, not in application
- Use connection pooling
- Monitor query execution plans
- Consider materialized views for complex aggregations

### 11.9 Security Considerations
- Authentication is currently disabled (TEMPORARILY DISABLED)
- When enabled, always enforce authentication
- Validate all user inputs
- Sanitize text search patterns
- Log security-relevant events
- Consider tenant isolation if multi-tenant

### 11.10 Testing Considerations
- Test with empty result sets
- Test with single result
- Test with maximum page size
- Test with large offsets
- Test with all filter combinations
- Test version filtering edge cases (single version, multiple versions)
- Test with missing optional data (deployment, etc.)
- Performance test with realistic data volumes
- Test NULL value handling extensively

---

## 12. RESPONSE STRUCTURE

### 12.1 Success Response
```json
{
  "process_definitions": [
    {
      "id": "string",
      "key": "string",
      "name": "string",
      "version": "integer",
      "category": "string",
      "deployment_id": "string",
      "resource_name": "string",
      "diagram_resource_name": "string|null",
      "has_start_form": "boolean",
      "suspension_state": "integer",
      "tenant_id": "string|null",
      "version_tag": "string|null",
      "history_ttl": "integer|null",
      "startable": "boolean",
      "is_active": "boolean",
      "is_suspended": "boolean",
      "created": "ISO8601|null",
      "deployment_time": "ISO8601|null"
    }
  ],
  "total_count": "integer",
  "limit": "integer",
  "offset": "integer",
  "has_more": "boolean"
}
```

### 12.2 Error Response
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message"
  }
}
```

**Error Codes:**
- VALIDATION_INVALID_INPUT: Invalid input parameters (e.g., invalid sort_by)
- DATABASE_QUERY_FAILED: Database error occurred
- INTERNAL_SERVER_ERROR: Unexpected server error

**HTTP Status Codes:**
- 200: Success
- 400: Validation error (invalid parameters)
- 500: Server error (database error or unexpected error)

---

## 13. SUMMARY

This documentation provides a complete business-level guide for implementing the process-definitions list functionality. Key points to remember:

1. **Single Data Source**: Use Process Definition table with optional Deployment join
2. **Comprehensive Filtering**: Support 8+ filter types with proper SQL-level implementation
3. **Version Management**: Support latest version filtering with two strategies
4. **Flexible Sorting**: Support 2 sort fields with proper NULL handling
5. **Efficient Pagination**: SQL-level pagination with total count
6. **Rich Data Assembly**: Enrich base data with computed fields and deployment information
7. **Performance First**: Use proper indexing, efficient subqueries, and fetch only needed data
8. **Error Resilience**: Handle missing data, database errors, and edge cases gracefully
9. **Metrics and Monitoring**: Track performance and errors for observability
10. **Design Patterns**: Use recommended patterns for maintainability and testability

Follow this documentation step-by-step to ensure a complete and correct implementation.
