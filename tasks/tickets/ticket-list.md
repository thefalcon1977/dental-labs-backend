# Ticket List Implementation Documentation

## Overview
This document provides a comprehensive business-level guide for reimplementing the ticket-list functionality. It covers all logic, filters, permissions, sorting, and data assembly requirements without any code implementation details.

---

## 1. BASE QUERY STRUCTURE

### 1.1 Data Sources
The ticket list uses a single data source:

**History Table (Process Instance History)**
- Contains all process instances: active, completed, cancelled, suspended, and externally terminated
- Stores complete historical data for all tickets
- Includes: process instance ID, business key, process definition info, start/end times, duration, creator, tenant ID, delete reason, suspension state
- Provides comprehensive data for all ticket states and statuses

### 1.2 Query Construction Strategy
- Build a single query from history table
- Apply all filters to the history query
- Query handles all ticket states (active, completed, cancelled, suspended, terminated)
- No need for union or deduplication logic

### 1.3 Required Joins

**For History Query:**
- Join with Process Definition table to get process name, category, and version
- Optional outer join with history titles table (act_hi_procinst_titles) to get instance title
- Handle gracefully if titles table doesn't exist (add NULL column)

### 1.4 Data Selection
Select the following fields from base queries:
- Process instance ID (proc_inst_id)
- Business key (ticket number)
- Process definition key and ID
- Process definition name (ticket type)
- Process definition category
- Process definition version
- Start time (create time)
- End time
- Duration
- Start user ID (creator)
- Delete reason
- Tenant ID
- Instance title (if available)

---

## 2. FILTERS

### 2.1 Filter Application Rules
- All filters are applied at SQL level using WHERE clauses or EXISTS subqueries
- Filters are applied to the history query
- Multiple filters are combined with AND logic
- Array/list filters use OR logic within the filter (e.g., multiple processors = any match)
- Filters are case-insensitive where appropriate (use ILIKE for text searches)

### 2.2 Text-Based Filters

**Ticket Type Filter (ticket_type)**
- Filter by process definition name
- Uses partial match (contains) with ILIKE pattern matching
- Pattern: `%{ticket_type}%`
- Applied to ProcessDefinition.name_ field

**Ticket Number Filter (ticket_number)**
- Filter by business key
- Uses partial match (contains) with ILIKE pattern matching
- Pattern: `%{ticket_number}%`
- Applied to business_key_ field in history table

**Ticket Title Filter (ticket_title)**
- Filter by instance title
- Uses partial match (contains) with ILIKE pattern matching
- Pattern: `%{ticket_title}%`
- Applied to instance_title_ from titles tables
- Only applied if titles table exists, otherwise skipped with warning

### 2.3 Status Filter (ticket_status)

**Status Values:**
- ACTIVE: Process is currently running (end_time is NULL)
- COMPLETED: Process finished successfully
- CANCELLED: Process was cancelled
- SUSPENDED: Process is suspended
- EXTERNALLY_TERMINATED: Process was terminated externally

**Status Logic:**
- ACTIVE: state_ == "ACTIVE"
- SUSPENDED: state_ == "SUSPENDED"
- COMPLETED: end_time is not NULL AND delete_reason is NULL
- CANCELLED: end_time is not NULL AND delete_reason is not NULL AND delete_reason does not contain "terminated"
- EXTERNALLY_TERMINATED: end_time is not NULL AND delete_reason contains "terminated" or "termination"
- When status is NULL: include all instances regardless of status

### 2.4 User-Based Filters

**Processor Filter (processor)**
- Filter by current assignee of active tasks
- Accepts comma-separated list of usernames (OR logic)
- Checks TaskHistory table for active tasks
- Checks TaskHistory.assignee_, IdentityLinkHistory.user_id_, IdentityLinkHistory.group_id_
- Only considers active tasks (end_time is NULL for the task)
- Uses EXISTS subqueries for performance

**Assignee Filter (assignee)**
- Filter by assignee across assignees, candidate_users, and candidate_groups
- Accepts comma-separated list of values (OR logic)
- Can be empty string to filter for tickets with no assignee
- If parameter not provided, filter is skipped entirely
- Checks TaskHistory.assignee_ for active tasks
- Only considers active tasks (end_time is NULL for the task)

**Creator Filter (creator)**
- Filter by start user (process instance creator)
- Accepts comma-separated list of user IDs (OR logic)
- Applied to ProcessInstanceHistory.start_user_id_ field
- Uses IN clause for multiple values

### 2.5 Phase Filter (current_phases)

**Filter Structure:**
- Accepts comma-separated list of phase names
- Uses OR logic: ticket matches if it has at least one of the specified phases as active
- Phase names are activity instance names (act_name_)

**Implementation:**
- Check ActivityInstanceHistory table for active phases
- Active phase: end_time is NULL
- Filter by act_name_ IN (phases list)
- Uses EXISTS subquery for performance

### 2.6 Time Range Filters

**Start Time From (start_time_from)**
- Filter tickets created on or after this date/time
- ISO 8601 format with timezone support
- Applied to ProcessInstanceHistory.start_time_
- Comparison: start_time_ >= start_time_from

**Start Time To (start_time_to)**
- Filter tickets created on or before this date/time
- ISO 8601 format with timezone support
- Applied to ProcessInstanceHistory.start_time_
- Comparison: start_time_ <= start_time_to

**End Time From (end_time_from)**
- Filter tickets ended on or after this date/time
- ISO 8601 format with timezone support
- Applied to ProcessInstanceHistory.end_time_
- Comparison: end_time_ >= end_time_from

**End Time To (end_time_to)**
- Filter tickets ended on or before this date/time
- ISO 8601 format with timezone support
- Applied to ProcessInstanceHistory.end_time_
- Comparison: end_time_ <= end_time_to

**Time Parsing:**
- Handle ISO 8601 format with 'Z' timezone indicator
- Convert 'Z' to '+00:00' for proper parsing
- Handle parsing errors gracefully (skip filter if invalid)

### 2.7 Special Filters

**Pending Basket Filter (pending_basket_ids)**
- Optional list filter for tickets directly assigned to user or where user is in candidates
- Provide comma-separated user/group IDs (username, UUID, group)
- Only checks active tasks (end_time is NULL for the task)
- Uses EXISTS subqueries for performance

**Processed By Filter (processed_by_basket_ids)**
- Optional list filter for tickets that have been processed/submitted by the user
- Provide comma-separated user/group IDs (username, UUID, group)
- Checks TaskHistory for completed tasks (end_time is not NULL, delete_reason is NULL or 'completed')
- Checks both assignee and identity links (candidate/assignee types)
- Uses EXISTS subquery for performance

---

## 3. PERMISSIONS (USER BASKET)

### 3.1 Permission Model Overview
The user basket determines which tickets a user can see based on their involvement and group membership. This is a critical security and visibility feature.

### 3.2 User Basket Structure
- user_id: Username from JWT token
- groups: List of group names from JWT token (may include leading slashes)
- current_user_id: Internal user ID (UUID) if available
- current_user_username: Username for display purposes

### 3.3 Permission Rules (OR Logic)
A ticket is visible to a user if ANY of the following conditions are met:

**Rule 1: User is Creator**
- ProcessInstanceHistory.start_user_id_ matches user_id or current_user_id
- Direct comparison using IN clause

**Rule 2: User is Current Assignee**
- User is assigned to any active task in the process instance
- Checks TaskHistory.assignee_ field
- Only active tasks (end_time is NULL for the task)
- Uses EXISTS subquery

**Rule 3: User is in Candidate Users**
- User's username or ID is in candidate_users for any active task
- Checks IdentityLinkHistory.user_id_ with type = "candidate"
- Only active tasks (end_time is NULL for the task)
- Uses EXISTS subquery with join

**Rule 4: User's Group is in Candidate Groups**
- Any of user's groups is in candidate_groups for any active task
- Checks IdentityLinkHistory.group_id_ with type = "candidate"
- Strips leading slashes from group names for matching
- Only active tasks (end_time is NULL for the task)
- Uses EXISTS subquery with join

**Rule 5: User Has Historical Involvement**
- User has completed at least one task in the process instance
- Checks TaskHistory.assignee_ where end_time is not NULL and delete_reason is NULL
- Uses EXISTS subquery

**Rule 6: User's Group Has Historical Involvement**
- Any member of user's groups has completed tasks in the process instance
- Checks IdentityLinkHistory with type = "candidate" or "assignee"
- Checks both user_id and group_id matches
- Only completed tasks (end_time is not NULL, delete_reason is NULL or 'completed')
- Uses EXISTS subquery with join

**Rule 7: User is in Same Group as Creator**
- User shares at least one group with the ticket creator
- Checks Membership and Group tables
- Compares creator's groups with user's groups
- Handles group name matching with/without leading slashes
- Uses EXISTS subquery with joins

### 3.4 Permission Implementation Notes
- All permission checks use EXISTS subqueries for performance
- Combine all conditions with OR logic
- Check both username and user_id for flexibility
- Clean group names (strip leading slashes) before matching
- Apply to history query
- If no user_basket provided, show all tickets (no filtering)

### 3.5 User ID Matching Strategy
- Primary: Use username from JWT token
- Secondary: Use current_user_id (UUID) if different from username
- Match against both values to handle different storage formats
- Some systems store usernames, others store UUIDs

---

## 4. SORTING

### 4.1 Sort Parameters
- sort_by: Field to sort by (default: "create_time")
- sort_order: "asc" or "desc" (default: "desc")

### 4.2 Supported Sort Fields

**create_time**
- Sort by process instance start time
- Uses ProcessInstanceHistory.start_time_
- NULL values handled with NULLS LAST

**end_time**
- Sort by process instance end time
- Uses ProcessInstanceHistory.end_time_
- NULL values handled with NULLS LAST

**ticket_number**
- Sort by business key (ticket number)
- Uses business_key_ field
- String comparison

**ticket_type**
- Sort by process definition name
- Uses ProcessDefinition.name_
- String comparison

**creator**
- Sort by start user ID (creator username)
- Uses ProcessInstanceHistory.start_user_id_
- String comparison

**duration**
- Sort by process duration
- Uses ProcessInstanceHistory.duration_ (milliseconds)
- NULL values handled appropriately

**processor**
- Sort by current processor (assignee)
- Extracted from active tasks
- Uses first processor found
- String comparison

**ticket_title**
- Sort by instance title
- Uses instance_title_ from titles tables
- NULL values handled with NULLS LAST

### 4.3 Sorting Implementation Strategy

**For History Query:**
1. Apply sorting directly to the query results
2. Use calculated/computed fields from the query
3. Handle NULL values consistently (NULLS LAST for both ASC and DESC)
4. Apply sort to final result set before pagination

**For SQL Function Approach:**
- Use CASE statements for dynamic sorting
- One CASE branch per sort field and order combination
- Only one branch will be non-NULL based on parameters
- Apply ORDER BY with all CASE expressions

**For Query Builder Approach:**
- Map sort_by to appropriate column reference
- Apply ORDER BY with sort_order direction
- Handle NULL values explicitly

### 4.4 Sort Order Handling
- Default to "desc" if not specified
- Case-insensitive comparison ("asc", "desc", "ASC", "DESC")
- NULL values always placed last regardless of sort order

### 4.5 Secondary Sort
- When primary sort values are equal, use process instance ID as tiebreaker
- Ensures consistent ordering across pagination

---

## 5. PAGINATION

### 5.1 Pagination Parameters
- limit: Number of items per page (default: 50, min: 1, max: 200)
- offset: Number of items to skip (default: 0, min: 0)

### 5.2 Pagination Strategy

**Two-Phase Approach:**
1. **Phase 1: Filter and Sort**
   - Apply all filters to history query
   - Apply sorting
   - Calculate total count

2. **Phase 2: Paginate**
   - Apply LIMIT and OFFSET to sorted results
   - Fetch full ticket data only for paginated subset
   - Return paginated results with total count

### 5.3 Intelligent Buffering
- Use dynamic buffer size for SQL pagination
- Formula: max(limit * 2, offset + limit * 1.5)
- Cap at maximum buffer size (e.g., 10,000) to avoid memory issues
- Ensures enough records are fetched to cover offset position

### 5.4 Total Count Calculation
- Calculate total count before pagination
- Count distinct process instance IDs after all filters applied
- Return total count with paginated results
- Used to calculate has_more flag

### 5.5 Has More Flag
- Calculate as: (offset + limit) < total_count
- Indicates if more pages are available
- Returned in response metadata

### 5.6 Performance Optimization
- Only fetch full ticket data (tasks, variables, etc.) for paginated subset
- Apply LIMIT/OFFSET at SQL level when possible
- Use streaming for large result sets
- Avoid loading all data into memory

---

## 6. DATA ASSEMBLY

### 6.1 Ticket Data Structure

**Core Fields:**
- ticket_id: Process instance ID
- ticket_number: Business key
- ticket_type: Process definition name
- ticket_status: Process state (ACTIVE, COMPLETED, etc.)
- ticket_title: Instance title (if available)
- creator: Start user ID (username)
- create_time: Start time (ISO 8601)
- end_time: End time (ISO 8601, nullable)
- duration: Process duration in milliseconds (nullable)

**User Assignment Fields:**
- processor: List of current assignees (from active tasks)
- processors: Alias for processor (for compatibility)
- assignee: Current assignee (single value, from active tasks)
- candidate_users: List of candidate user IDs/usernames
- candidate_groups: List of candidate group names

**Phase Information:**
- current_phases: List of active phase names (activity instance names where end_time is NULL)

**Severity Information:**
- severity_min: Minimum severity value across all tasks
- severity_max: Maximum severity value across all tasks
- severity_avg: Average severity value across all tasks
- severity_count: Count of tasks with severity (optional)
- sla_severity: Detailed severity mapping by task (optional)

**Task Information:**
- tasks: List of task objects with full details (fetched separately)

### 6.2 Data Enrichment Process

**Step 1: Base Data Collection**
- Fetch process instance data from history query
- Include process definition information
- Include instance titles if available

**Step 2: Current Activity Information**
- Fetch active activity instances for each process instance
- Extract phase names (activity names) where end_time is NULL
- Store as current_phases array

**Step 3: Processor/Assignee Information**
- Fetch active tasks (TaskHistory) for each process instance
- Extract assignees (TaskHistory.assignee_)
- Extract candidate users from IdentityLinkHistory (type = "candidate", user_id_)
- Extract candidate groups from IdentityLinkHistory (type = "candidate", group_id_)
- Only include active tasks (end_time is NULL for the task)

**Step 4: Severity Information**
- Fetch severity variables for each process instance
- Variables: name ends with "_sla_severity" or equals "_sla_severity"
- Extract values from text_, long_, or double_ columns
- Calculate min, max, average across all tasks
- Map severity to task IDs if detailed mapping needed

**Step 5: Task Details (Optional)**
- Fetch full task details for each process instance
- Include: task ID, name, definition key, assignee, start/end times, state, priority, due date
- Only fetch for paginated subset to optimize performance

**Step 6: User ID to Username Conversion**
- Convert user IDs to usernames for current user only
- Replace user_id with username in creator, assignee, processor, candidate_users fields
- Only convert if current_user_id and current_user_username provided

### 6.3 Data Source
- All data is fetched from history table
- No need for data source priority or deduplication
- Single source ensures consistent data representation

### 6.4 Null Handling
- Return empty arrays [] instead of NULL for list fields
- Return NULL for optional single-value fields (end_time, duration, etc.)
- Handle missing titles gracefully (return NULL or empty string)

### 6.5 Response Format
- tickets: Array of ticket objects
- total_count: Total number of tickets matching filters
- limit: Requested page size
- offset: Requested offset
- has_more: Boolean indicating more pages available
- performance_metrics: Optional performance tracking data

---

## 7. PERFORMANCE CONSIDERATIONS

### 7.1 Query Optimization
- Use EXISTS subqueries instead of JOINs for filters when possible
- Apply filters at SQL level, not in application code
- Use indexes on frequently filtered columns:
  - Process instance ID
  - Business key
  - Start user ID
  - Start/end times
  - Process definition ID/key
  - Task assignee
  - Identity link user/group IDs

### 7.2 Indexing Requirements
**Critical Indexes:**
- Process instance ID (primary key, foreign keys)
- Business key (for ticket number searches)
- Start user ID (for creator filter)
- Start/end times (for time range filters)
- Process definition ID/key (for ticket type filter)
- Task process instance ID + assignee (for processor/assignee filters)
- Identity link task ID + type + user_id/group_id (for permission checks)
- Activity instance process instance ID + end_time (for phase filter)
- Variable process instance ID + name (for severity filter)

### 7.3 Query Execution Strategy
- Execute history query with optimized execution plan
- Use connection pooling for database connections
- Stream large result sets instead of loading into memory
- Limit data fetched to only required fields
- Fetch detailed data (tasks, variables) only for paginated subset

### 7.4 Caching Considerations
- Cache process definition data (names, categories) - changes infrequently
- Consider caching user group memberships - changes infrequently
- Don't cache ticket data - changes frequently
- Cache total counts with short TTL if acceptable

### 7.5 Monitoring and Metrics
- Track query execution times
- Monitor database query counts
- Track pagination buffer sizes
- Monitor memory usage for large result sets
- Log slow queries for optimization

---

## 8. ERROR HANDLING

### 8.1 Input Validation
- Validate limit: 1 <= limit <= 200
- Validate offset: offset >= 0
- Validate ticket_status: Must be valid enum value or raise error
- Validate time formats: ISO 8601 with timezone support
- Validate sort_by: Must be supported field or use default
- Validate sort_order: Must be "asc" or "desc" or use default

### 8.2 Database Error Handling
- Handle connection errors gracefully
- Handle query timeout errors
- Handle missing table errors (titles tables) gracefully
- Log all database errors with context
- Return appropriate HTTP status codes (500 for database errors)

### 8.3 Missing Data Handling
- Handle missing titles tables gracefully (skip title filter/join)
- Handle missing process definitions gracefully (skip join, use NULL)
- Handle missing user data gracefully (skip user ID conversion)
- Return partial data when non-critical data is missing

### 8.4 Authentication Errors
- Require JWT authentication for all requests
- Return 401 if authentication fails
- Extract user information from JWT token
- Handle missing user groups gracefully (empty array)

---

## 9. IMPLEMENTATION TASKS

### Task 1: Base Query Construction
1. Create history query with required joins (process definition, titles)
2. Handle missing tables gracefully
3. Ensure query handles all ticket states (active, completed, cancelled, suspended, terminated)

### Task 2: Filter Implementation
1. Implement text-based filters (ticket_type, ticket_number, ticket_title)
2. Implement status filter with proper logic for all states
3. Implement user-based filters (processor, assignee, creator)
4. Implement phase filter with OR logic
5. Implement time range filters with proper parsing
6. Implement severity filters with aggregation
7. Implement special filters (pending_basket_ids, processed_by_basket_ids)

### Task 3: Permission System
1. Extract user information from JWT token
2. Implement all 7 permission rules
3. Combine permission rules with OR logic
4. Apply permissions to history query
5. Handle user ID/username matching
6. Handle group name cleaning (strip slashes)

### Task 4: Sorting Implementation
1. Map sort fields to database columns
2. Implement sorting for history query results
3. Handle NULL values consistently
4. Implement secondary sort (process instance ID)
5. Support all sort fields (create_time, end_time, ticket_number, etc.)

### Task 5: Pagination System
1. Calculate total count after filters
2. Implement intelligent buffering
3. Apply LIMIT/OFFSET at SQL level
4. Fetch full data only for paginated subset
5. Calculate has_more flag

### Task 6: Data Assembly
1. Collect base process instance data
2. Fetch and attach current activity information
3. Fetch and attach processor/assignee information
4. Fetch and attach severity information
5. Fetch and attach task details (optional)
6. Convert user IDs to usernames
7. Format response structure

### Task 7: Performance Optimization
1. Create required database indexes
2. Optimize query execution plans
3. Implement query result streaming
4. Add performance monitoring
5. Optimize data fetching (only paginated subset)

### Task 8: Error Handling
1. Implement input validation
2. Handle database errors gracefully
3. Handle missing data gracefully
4. Implement authentication checks
5. Add comprehensive logging

### Task 9: Testing
1. Test all filter combinations
2. Test permission rules individually and combined
3. Test sorting with all fields and orders
4. Test pagination edge cases (first page, last page, empty results)
5. Test error scenarios
6. Performance testing with large datasets

---

## 10. DESIGN PATTERNS RECOMMENDATIONS

### 10.1 Overview
To implement the ticket-list functionality effectively, several design patterns are recommended to ensure maintainability, testability, and scalability. This section outlines the recommended patterns with their priorities and implementation guidance.

### 10.2 Pattern Priority Classification

**MUST HAVE (Critical for Core Functionality):**
- Specification Pattern
- Builder Pattern
- Repository Pattern

**SHOULD HAVE (Important for Flexibility):**
- Strategy Pattern
- Template Method Pattern

**NICE TO HAVE (Enhancement Opportunities):**
- Decorator Pattern
- Factory Pattern

### 10.3 Recommended Patterns

#### 10.3.1 Specification Pattern (MUST HAVE)

**Purpose:** Build complex filter criteria dynamically and composably.

**Why Essential:**
- 15+ filter types need to be combined flexibly
- Filters must work with AND/OR logic
- Each filter should be independently testable
- Easy to add new filters without modifying existing code

**Implementation Guidance:**
- Create base `ISpecification` interface with `is_satisfied_by()` method
- Implement individual specifications: `TicketTypeSpecification`, `CreatorSpecification`, `StatusSpecification`, etc.
- Create composite specifications: `AndSpecification`, `OrSpecification`
- Apply specifications to history query
- Each specification encapsulates SQL WHERE clause logic

**Benefits:**
- Composable: `AndSpecification(filter1, OrSpecification(filter2, filter3))`
- Testable: Each specification can be unit tested independently
- Maintainable: New filters don't affect existing ones
- Reusable: Specifications work consistently with history table

#### 10.3.2 Builder Pattern (MUST HAVE)

**Purpose:** Construct complex queries step by step with a fluent, readable API.

**Why Essential:**
- Many optional parameters (filters, sorting, pagination)
- Complex query construction needs clear structure
- Improves code readability and maintainability
- Handles all ticket states from single history source

**Implementation Guidance:**
- Create `TicketQueryBuilder` class
- Methods: `withFilter()`, `withSorting()`, `withPagination()`, `withPermissions()`
- Final `build()` method returns executable query
- Support method chaining for fluent API

**Example Structure:**
```
TicketQueryBuilder
  .withFilter(ticketTypeSpecification)
  .withFilter(creatorSpecification)
  .withSorting(sortBy, sortOrder)
  .withPagination(limit, offset)
  .withPermissions(userBasket)
  .build()
```

**Benefits:**
- Readable: Clear intent of query construction
- Flexible: Easy to add new builder methods
- Type-safe: Compile-time checking of query structure
- Testable: Can mock builders for testing

#### 10.3.3 Repository Pattern (MUST HAVE)

**Purpose:** Abstract data access layer and provide clean interface for ticket operations.

**Why Essential:**
- Complex queries from history table should be encapsulated
- Handles tasks, variables, and related data from history
- Easier testing with mock repositories
- Separation of concerns (business logic vs data access)

**Implementation Guidance:**
- Create `ITicketRepository` interface
- Implement `TicketRepository` with methods:
  - `findTickets(specification, sorting, pagination)`
  - `enrichTicketData(ticketIds)`
- Repository handles all SQL query construction from history table
- Service layer uses repository, not direct database access

**Benefits:**
- Abstraction: Business logic doesn't depend on database structure
- Testable: Easy to create mock repositories
- Maintainable: Database changes isolated to repository
- Reusable: Repository can be used by multiple services

#### 10.3.4 Strategy Pattern (SHOULD HAVE)

**Purpose:** Encapsulate different algorithms for sorting, filtering, and data enrichment.

**Why Important:**
- 9+ sort fields with different implementations
- Different filter strategies (text, date, user-based, severity)
- Different data enrichment strategies
- Easy to add new strategies without modifying existing code

**Implementation Guidance:**
- Create `SortStrategy` interface with `apply_sort(query, order)` method
- Implement strategies: `CreateTimeSortStrategy`, `EndTimeSortStrategy`, `SeveritySortStrategy`, etc.
- Create `FilterStrategy` interface for different filter types
- Create `EnrichmentStrategy` interface for data enrichment steps
- Use factory or registry to select appropriate strategy

**Use Cases:**
- Sort Strategies: Different SQL ORDER BY clauses based on field
- Filter Strategies: TextFilterStrategy (ILIKE), DateFilterStrategy (range), UserFilterStrategy (EXISTS)
- Enrichment Strategies: ActivityEnrichmentStrategy, ProcessorEnrichmentStrategy, SeverityEnrichmentStrategy

**Benefits:**
- Extensible: Add new strategies without changing existing code
- Testable: Each strategy independently testable
- Flexible: Can swap strategies at runtime
- Maintainable: Strategy logic isolated and focused

#### 10.3.5 Template Method Pattern (SHOULD HAVE)

**Purpose:** Define the skeleton of the ticket listing algorithm, allowing subclasses to override specific steps.

**Why Important:**
- Consistent execution flow for ticket listing
- Ensures correct order of operations (filter → sort → paginate → enrich)
- Allows customization of specific steps while maintaining overall structure

**Implementation Guidance:**
- Create `TicketListService` base class with template method `listTickets()`
- Define steps: `buildQueries()`, `applyFilters()`, `combineResults()`, `applySorting()`, `applyPagination()`, `enrichData()`
- Subclasses can override specific steps if needed
- Template method ensures correct execution order

**Benefits:**
- Consistency: Same flow for all ticket listing operations
- Maintainability: Changes to flow happen in one place
- Flexibility: Override specific steps when needed
- Clear structure: Easy to understand execution flow

#### 10.3.6 Decorator Pattern (NICE TO HAVE)

**Purpose:** Dynamically add responsibilities (data enrichment) to ticket objects.

**Why Useful:**
- Data assembly happens in multiple steps
- Each step adds specific data (activities, processors, severity, tasks)
- Can be applied conditionally
- Allows flexible composition of enrichment steps

**Implementation Guidance:**
- Create `TicketDecorator` base class
- Implement decorators: `ActivityDecorator`, `ProcessorDecorator`, `SeverityDecorator`, `TaskDecorator`
- Each decorator adds specific fields to ticket object
- Chain decorators: `new TaskDecorator(new SeverityDecorator(new ProcessorDecorator(baseTicket)))`

**Benefits:**
- Flexible: Compose enrichment steps as needed
- Extensible: Add new decorators without changing existing ones
- Optional: Can skip enrichment steps for performance
- Testable: Each decorator independently testable

#### 10.3.7 Factory Pattern (NICE TO HAVE)

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

### 10.4 Recommended Architecture

```
┌─────────────────────────────────────────────────┐
│         TicketListService                        │
│    (Template Method - Orchestrator)             │
│  - listTickets(specifications, sorting, etc.)   │
└──────────────┬──────────────────────────────────┘
               │
       ┌───────┴──────────────┐
       │                      │
┌──────▼──────────┐  ┌────────▼────────────┐
│  Repository     │  │  Specification      │
│   Pattern       │  │   Pattern           │
│                 │  │                     │
│ ITicketRepo     │  │ ISpecification      │
│  - findTickets()│  │  - is_satisfied_by()│
└──────┬──────────┘  └────────┬────────────┘
       │                      │
┌──────▼──────────────────────▼────────────┐
│      QueryBuilder (Builder Pattern)      │
│  - TicketQueryBuilder                    │
│  - withFilter(specification)            │
│  - withSorting(strategy)                │
│  - withPagination(limit, offset)         │
└──────┬───────────────────────────────────┘
       │
┌──────▼───────────────────────────────────┐
│   Filter/Sort Strategies (Strategy)     │
│  - TextFilterStrategy                    │
│  - DateFilterStrategy                    │
│  - UserFilterStrategy                    │
│  - PermissionFilterStrategy              │
│  - CreateTimeSortStrategy                │
│  - SeveritySortStrategy                  │
└──────┬───────────────────────────────────┘
       │
┌──────▼───────────────────────────────────┐
│   Data Enrichment (Decorator Pattern)   │
│  - ActivityEnricher                      │
│  - ProcessorEnricher                     │
│  - SeverityEnricher                      │
│  - TaskEnricher                          │
└──────────────────────────────────────────┘
```

### 10.5 Implementation Priority

**Phase 1: Core Patterns (Start Here)**
1. Repository Pattern - Establish data access abstraction
2. Specification Pattern - Implement core filtering logic
3. Builder Pattern - Build query construction system

**Phase 2: Enhancement Patterns**
4. Strategy Pattern - Add sorting and filter variations
5. Template Method Pattern - Define execution flow

**Phase 3: Optimization Patterns**
6. Decorator Pattern - Optimize data enrichment
7. Factory Pattern - Centralize object creation

### 10.6 Pattern Benefits Summary

**Maintainability:**
- Easy to add new filters without modifying existing code
- Clear separation of concerns
- Changes isolated to specific components

**Testability:**
- Each component can be unit tested independently
- Easy to create mocks for testing
- Test filters, sorting, and enrichment separately

**Performance:**
- Optimize individual components
- Cache strategies can be added per component
- Query optimization isolated to repository

**Flexibility:**
- Swap implementations without affecting other parts
- Add new features by adding new strategies/specifications
- Support different filter and sort combinations with same patterns

**Scalability:**
- Patterns support growth in filter types
- Easy to extend with new data enrichment steps
- Patterns handle complexity gracefully

### 10.7 Additional Considerations

**Value Objects:**
- Represent filters, sorting, pagination as immutable value objects
- Ensures type safety and prevents invalid states
- Examples: `FilterCriteria`, `SortCriteria`, `PaginationCriteria`

**Query Object Pattern:**
- Encapsulate all query parameters in a single `TicketQuery` object
- Pass query object through layers instead of many parameters
- Makes API cleaner and easier to extend

**Service Layer Pattern:**
- Separate business logic from data access
- `TicketListService` orchestrates repository and specifications
- Handles business rules and validation

**DTO Pattern:**
- Use Data Transfer Objects for API responses
- Separate internal domain models from API contracts
- Easier to version APIs

### 10.8 Pattern Implementation Tips

**Specification Pattern:**
- Keep specifications stateless when possible
- Use specifications for both filtering and validation
- Consider caching SQL generation for performance

**Builder Pattern:**
- Validate builder state in `build()` method
- Support both fluent and step-by-step construction
- Consider builder validation for complex queries

**Repository Pattern:**
- Keep repository focused on data access only
- Don't put business logic in repository
- Use repository for both read and write operations if needed

**Strategy Pattern:**
- Use strategy registry or factory to select strategies
- Consider strategy caching for frequently used strategies
- Make strategies stateless when possible

**Template Method Pattern:**
- Keep template method simple and focused
- Use hooks for optional steps
- Document which methods can be overridden

### 10.9 Anti-Patterns to Avoid

**Avoid:**
- God Object: Don't put everything in one class
- Anemic Domain Model: Don't make objects just data containers
- Premature Optimization: Start simple, optimize based on metrics
- Over-Engineering: Don't use patterns where simple code works
- Tight Coupling: Keep dependencies loose and testable

**Instead:**
- Single Responsibility: Each class has one reason to change
- Dependency Injection: Inject dependencies, don't create them
- Interface Segregation: Keep interfaces focused and small
- Open/Closed Principle: Open for extension, closed for modification

---

## 11. IMPORTANT NOTES AND TIPS

### 11.1 Data Consistency
- All data is retrieved from history table
- Ensure business_key is retrieved correctly from process instance
- History table contains all process instances regardless of state
- No need to handle multiple data sources

### 11.2 User Identification
- System may store usernames or UUIDs in different places
- Always check both username and user_id for matching
- JWT token provides username, but database may use UUID
- Maintain mapping between user_id and username if needed

### 11.3 Group Name Handling
- Group names may have leading slashes (e.g., "/group-name")
- Strip leading slashes before matching
- Handle both formats in permission checks
- Maintain consistency in group name storage

### 11.4 Task State Handling
- Only consider active tasks for processor/assignee filters
- Active task: end_time is NULL for the task
- Completed task: end_time is not NULL and delete_reason is NULL or 'completed'
- Use task history table to determine task state

### 11.5 Severity Calculation
- Severity values may be in text_, long_, or double_ columns
- Handle empty strings by converting to NULL
- Use COALESCE to try all three columns
- Cast to integer for comparison
- Lower number = higher priority (1 = highest)

### 11.6 Time Handling
- Store and compare times in UTC
- Support ISO 8601 format with timezone
- Convert 'Z' timezone indicator to '+00:00'
- Handle timezone conversions properly
- Use database timestamp types for storage

### 11.7 Pagination Best Practices
- Always calculate total count before pagination
- Use intelligent buffering to handle large offsets
- Fetch detailed data only for current page
- Stream large result sets when possible
- Monitor memory usage for large datasets

### 11.8 Performance Tips
- Use EXISTS instead of JOINs for existence checks
- Apply filters at SQL level, not in application
- Create indexes on all filtered/sorted columns
- Use connection pooling
- Monitor query execution plans
- Consider materialized views for complex aggregations

### 11.9 Security Considerations
- Always enforce authentication
- Apply permission filters at SQL level (never trust application-level filtering)
- Validate all user inputs
- Sanitize text search patterns
- Log security-relevant events
- Never expose internal user IDs unnecessarily

### 11.10 Testing Considerations
- Test with empty result sets
- Test with single result
- Test with maximum page size
- Test with large offsets
- Test with all filter combinations
- Test permission edge cases (user in multiple groups, etc.)
- Test with missing optional data (titles, etc.)
- Performance test with realistic data volumes

---

## 12. RESPONSE STRUCTURE

### 12.1 Success Response
```
{
  "tickets": [
    {
      "ticket_id": "string",
      "ticket_number": "string",
      "ticket_type": "string",
      "ticket_status": "ACTIVE|COMPLETED|CANCELLED|SUSPENDED|EXTERNALLY_TERMINATED",
      "ticket_title": "string|null",
      "creator": "string",
      "create_time": "ISO8601",
      "end_time": "ISO8601|null",
      "duration": "number|null",
      "processor": ["string"],
      "processors": ["string"],
      "assignee": "string|null",
      "current_phases": ["string"],
      "candidate_users": ["string"],
      "candidate_groups": ["string"],
      "severity_min": "number|null",
      "severity_max": "number|null",
      "severity_avg": "number|null",
      "tasks": ["task objects"]
    }
  ],
  "total_count": "number",
  "limit": "number",
  "offset": "number",
  "has_more": "boolean",
  "performance_metrics": {
    "total_execution_time": "number",
    "total_queries": "number",
    "sql_optimized": "boolean"
  }
}
```

### 12.2 Error Response
```
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message"
  }
}
```

**Error Codes:**
- DATABASE_QUERY_FAILED: Database error occurred
- INVALID_TICKET_STATUS: Invalid ticket_status value
- AUTHENTICATION_REQUIRED: JWT token missing or invalid
- INTERNAL_SERVER_ERROR: Unexpected server error

---

## 13. SUMMARY

This documentation provides a complete business-level guide for implementing the ticket-list functionality. Key points to remember:

1. **Single Data Source**: Use history table for all ticket data (active, completed, cancelled, suspended, terminated)
2. **Comprehensive Filtering**: Support 15+ filter types with proper SQL-level implementation
3. **Robust Permissions**: 7 permission rules ensure users only see appropriate tickets
4. **Flexible Sorting**: Support 9+ sort fields with proper NULL handling
5. **Efficient Pagination**: Intelligent buffering and SQL-level pagination
6. **Rich Data Assembly**: Enrich base data with activities, processors, severity, and tasks
7. **Performance First**: Use EXISTS subqueries, proper indexing, and fetch only needed data
8. **Error Resilience**: Handle missing data, database errors, and edge cases gracefully

Follow this documentation step-by-step to ensure a complete and correct implementation.
