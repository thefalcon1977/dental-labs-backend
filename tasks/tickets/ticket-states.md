# States API Implementation Documentation

## Overview
This document provides a comprehensive business-level guide for implementing the states functionality. It covers all logic, data structures, and response formats without any code implementation details.

The States API provides a catalog of all workflow states used in the Camunda workflow engine. It returns static state definitions organized by category, including process instance states, activity instance states, user task states, external task states, job states, and case instance states. This endpoint is read-only and returns hardcoded state definitions (no database queries).

---

## 1. BASE DATA STRUCTURE

### 1.1 Data Source
The states functionality uses **no database** - all state definitions are hardcoded in enum classes:

**State Enums (Hardcoded)**
- ProcessInstanceState enum
- ActivityInstanceState enum
- UserTaskState enum
- ExternalTaskState enum
- JobState enum
- CaseInstanceState enum

### 1.2 State Categories

**Process Instance States:**
- ACTIVE: Process is currently running
- SUSPENDED: Process is suspended (paused)
- COMPLETED: Process finished successfully
- CANCELLED: Process was cancelled
- EXTERNALLY_TERMINATED: Process was terminated externally

**Activity Instance States:**
- STARTED: Activity has started execution
- CANCELED: Activity was cancelled
- COMPLETED: Activity completed successfully
- DELETED: Activity was deleted

**User Task States:**
- CREATED: User task has been created
- ASSIGNED: User task has been assigned to a user
- SUSPENDED: User task is suspended
- COMPLETED: User task has been completed
- CANCELLED: User task was cancelled

**External Task States:**
- CREATED: External task has been created
- LOCKED: External task is locked for processing
- SUSPENDED: External task is suspended
- COMPLETED: External task completed successfully
- FAILED: External task execution failed
- ERROR: External task encountered an error

**Job States:**
- CREATED: Job has been created
- SUSPENDED: Job is suspended
- EXECUTING: Job is currently executing
- FAILED: Job execution failed
- DEADLETTER: Job moved to dead letter queue
- COMPLETED: Job completed successfully

**Case Instance States (CMMN):**
- ACTIVE: Case instance is active
- SUSPENDED: Case instance is suspended
- COMPLETED: Case instance completed successfully
- TERMINATED: Case instance was terminated
- CLOSED: Case instance is closed

---

## 2. ENDPOINTS

### 2.1 GET `/states/`
**Purpose:** Get comprehensive catalog of all workflow states

**Authentication:** Not required

**Query Parameters:** None

**Business Logic:**
1. Retrieve all state values from each enum class
2. Organize states by category
3. Create StateCategory objects for each category with:
   - List of state values (strings)
   - Description of the category
4. Create WorkflowStateCatalog containing all categories
5. Return catalog with all state categories

**State Retrieval:**
- Extract all enum values from ProcessInstanceState enum
- Extract all enum values from ActivityInstanceState enum
- Extract all enum values from UserTaskState enum
- Extract all enum values from ExternalTaskState enum
- Extract all enum values from JobState enum
- Extract all enum values from CaseInstanceState enum
- Convert enum values to strings

**Category Descriptions:**
- Process Instance States: "Process instance states - a process instance can be in one of these states"
- Activity Instance States: "Activity instance states from ACT_HI_ACTINST table"
- User Task States: "User task states for human tasks"
- External Task States: "External task states for system integration tasks"
- Job States: "Job states for async continuations, timers, and external tasks"
- Case Instance States: "Case instance states (CMMN - Case Management Model and Notation)"

**Response:** 200 OK with WorkflowStateCatalog

**Error Responses:**
- 500: Internal server error (if enum retrieval fails)

---

## 3. STATE DEFINITIONS

### 3.1 Process Instance States

**ACTIVE**
- Description: Process is currently running
- Usage: Process instance is executing
- Database Mapping: suspension_state = 1 (or NULL), end_time is NULL

**SUSPENDED**
- Description: Process is suspended (paused)
- Usage: Process execution is paused, can be resumed
- Database Mapping: suspension_state = 2

**COMPLETED**
- Description: Process finished successfully
- Usage: Process reached end event successfully
- Database Mapping: end_time is not NULL, delete_reason is NULL

**CANCELLED**
- Description: Process was cancelled
- Usage: Process was cancelled before completion
- Database Mapping: end_time is not NULL, delete_reason is not NULL and doesn't contain "terminated"

**EXTERNALLY_TERMINATED**
- Description: Process was terminated externally
- Usage: Process was terminated by external system or user action
- Database Mapping: end_time is not NULL, delete_reason contains "terminated" or "termination"

### 3.2 Activity Instance States

**STARTED**
- Description: Activity has started execution
- Usage: Activity instance has begun processing
- Source: ACT_HI_ACTINST table

**CANCELED**
- Description: Activity was cancelled
- Usage: Activity execution was cancelled before completion
- Source: ACT_HI_ACTINST table

**COMPLETED**
- Description: Activity completed successfully
- Usage: Activity finished execution successfully
- Source: ACT_HI_ACTINST table

**DELETED**
- Description: Activity was deleted
- Usage: Activity instance was removed
- Source: ACT_HI_ACTINST table

### 3.3 User Task States

**CREATED**
- Description: User task has been created
- Usage: Task exists but not yet assigned
- Source: Task history tables

**ASSIGNED**
- Description: User task has been assigned to a user
- Usage: Task is assigned to specific user
- Source: Task history tables

**SUSPENDED**
- Description: User task is suspended
- Usage: Task execution is paused
- Source: Task history tables

**COMPLETED**
- Description: User task has been completed
- Usage: Task was finished by user
- Source: Task history tables

**CANCELLED**
- Description: User task was cancelled
- Usage: Task was cancelled before completion
- Source: Task history tables

### 3.4 External Task States

**CREATED**
- Description: External task has been created
- Usage: Task exists, waiting for external system to fetch
- Source: External task tables

**LOCKED**
- Description: External task is locked for processing
- Usage: External system has locked task for processing
- Source: External task tables

**SUSPENDED**
- Description: External task is suspended
- Usage: Task execution is paused
- Source: External task tables

**COMPLETED**
- Description: External task completed successfully
- Usage: External system completed task successfully
- Source: External task tables

**FAILED**
- Description: External task execution failed
- Usage: Task execution failed, may be retried
- Source: External task tables

**ERROR**
- Description: External task encountered an error
- Usage: Task encountered error during execution
- Source: External task tables

### 3.5 Job States

**CREATED**
- Description: Job has been created
- Usage: Job exists, waiting to be executed
- Source: Job tables

**SUSPENDED**
- Description: Job is suspended
- Usage: Job execution is paused
- Source: Job tables

**EXECUTING**
- Description: Job is currently executing
- Usage: Job is actively running
- Source: Job tables

**FAILED**
- Description: Job execution failed
- Usage: Job failed during execution, may be retried
- Source: Job tables

**DEADLETTER**
- Description: Job moved to dead letter queue
- Usage: Job failed repeatedly and moved to dead letter queue
- Source: Job tables

**COMPLETED**
- Description: Job completed successfully
- Usage: Job finished execution successfully
- Source: Job tables

### 3.6 Case Instance States (CMMN)

**ACTIVE**
- Description: Case instance is active
- Usage: Case is currently active and processing
- Source: Case instance tables

**SUSPENDED**
- Description: Case instance is suspended
- Usage: Case execution is paused
- Source: Case instance tables

**COMPLETED**
- Description: Case instance completed successfully
- Usage: Case reached completion successfully
- Source: Case instance tables

**TERMINATED**
- Description: Case instance was terminated
- Usage: Case was terminated before completion
- Source: Case instance tables

**CLOSED**
- Description: Case instance is closed
- Usage: Case is closed (final state)
- Source: Case instance tables

---

## 4. RESPONSE STRUCTURE

### 4.1 WorkflowStateCatalog Schema
**Purpose:** Response schema for state catalog

**Structure:**
- process_instance_states: StateCategory
- activity_instance_states: StateCategory
- user_task_states: StateCategory
- external_task_states: StateCategory
- job_states: StateCategory
- case_instance_states: StateCategory

### 4.2 StateCategory Schema
**Purpose:** Schema for a category of states

**Fields:**
- states: list[string] (array of state values)
- description: string (description of the category)

### 4.3 Response Example
```json
{
  "process_instance_states": {
    "states": ["ACTIVE", "SUSPENDED", "COMPLETED", "CANCELLED", "EXTERNALLY_TERMINATED"],
    "description": "Process instance states - a process instance can be in one of these states"
  },
  "activity_instance_states": {
    "states": ["STARTED", "CANCELED", "COMPLETED", "DELETED"],
    "description": "Activity instance states from ACT_HI_ACTINST table"
  },
  "user_task_states": {
    "states": ["CREATED", "ASSIGNED", "SUSPENDED", "COMPLETED", "CANCELLED"],
    "description": "User task states for human tasks"
  },
  "external_task_states": {
    "states": ["CREATED", "LOCKED", "SUSPENDED", "COMPLETED", "FAILED", "ERROR"],
    "description": "External task states for system integration tasks"
  },
  "job_states": {
    "states": ["CREATED", "SUSPENDED", "EXECUTING", "FAILED", "DEADLETTER", "COMPLETED"],
    "description": "Job states for async continuations, timers, and external tasks"
  },
  "case_instance_states": {
    "states": ["ACTIVE", "SUSPENDED", "COMPLETED", "TERMINATED", "CLOSED"],
    "description": "Case instance states (CMMN - Case Management Model and Notation)"
  }
}
```

---

## 5. STATE USAGE

### 5.1 Process Instance States Usage
- Used for filtering process instances by state
- Used in ticket status filtering
- Used in search queries
- Used in reporting and analytics
- Mapped from database fields (suspension_state, end_time, delete_reason)

### 5.2 Activity Instance States Usage
- Used for filtering activity instances
- Used in activity history queries
- Used in process flow analysis
- Retrieved from ACT_HI_ACTINST table

### 5.3 User Task States Usage
- Used for filtering user tasks
- Used in task assignment logic
- Used in task completion tracking
- Retrieved from task history tables

### 5.4 External Task States Usage
- Used for filtering external tasks
- Used in external task processing
- Used in integration monitoring
- Retrieved from external task tables

### 5.5 Job States Usage
- Used for filtering jobs
- Used in job execution monitoring
- Used in job retry logic
- Retrieved from job tables

### 5.6 Case Instance States Usage
- Used for filtering case instances
- Used in case management
- Used in CMMN process tracking
- Retrieved from case instance tables

---

## 6. STATE MAPPING

### 6.1 Process Instance State Mapping
States are determined from database fields:

**ACTIVE:**
- suspension_state = 1 (or NULL)
- end_time is NULL

**SUSPENDED:**
- suspension_state = 2

**COMPLETED:**
- end_time is not NULL
- delete_reason is NULL

**CANCELLED:**
- end_time is not NULL
- delete_reason is not NULL
- delete_reason does not contain "terminated"

**EXTERNALLY_TERMINATED:**
- end_time is not NULL
- delete_reason contains "terminated" or "termination"

### 6.2 State Determination Logic
- Runtime instances: Use suspension_state to determine ACTIVE or SUSPENDED
- History instances: Use end_time and delete_reason to determine COMPLETED, CANCELLED, or EXTERNALLY_TERMINATED
- If end_time is NULL: Process is ACTIVE (if suspension_state = 1) or SUSPENDED (if suspension_state = 2)

---

## 7. METRICS AND MONITORING

### 7.1 Performance Metrics

**Request Timing:**
- Start performance timer at beginning of request
- Calculate duration at end of request
- Record duration for all requests (success and error)

**Business Event Metrics:**
- Record business event: event type, category, status
- Event type: "camunda_states_retrieved"
- Event category: "states"
- Status: "success" or "error"
- Duration: Request execution time

**HTTP Request Metrics:**
- Record HTTP request: method, endpoint, status code, duration
- Method: "GET"
- Endpoint: "/workflow-engine/states/"
- Status code: 200 (success), 500 (server error)
- Duration: Request execution time

### 7.2 Error Metrics
- Record error metrics if exception occurs
- Log error details
- Return 500 status code on error

---

## 8. ERROR HANDLING

### 8.1 Server Errors
- Return 500 Internal Server Error
- Used for: Unexpected exceptions during enum retrieval
- Error details logged server-side
- Full exception information captured

### 8.2 Error Logging
- All errors are logged with context
- Logs include: Error type, error message
- Exceptions are logged with full stack trace

---

## 9. PERFORMANCE CONSIDERATIONS

### 9.1 No Database Queries
- Endpoint performs no database queries
- All data is retrieved from enum classes
- Very fast response time
- No database load

### 9.2 Caching Considerations
- Response is static (doesn't change)
- Can be cached indefinitely
- Consider HTTP caching headers
- Client-side caching recommended

### 9.3 Response Size
- Response is small (just state lists)
- No pagination needed
- Fast to serialize
- Minimal network overhead

---

## 10. IMPLEMENTATION TASKS

### Task 1: Enum Definitions
1. Create ProcessInstanceState enum with all values
2. Create ActivityInstanceState enum with all values
3. Create UserTaskState enum with all values
4. Create ExternalTaskState enum with all values
5. Create JobState enum with all values
6. Create CaseInstanceState enum with all values

### Task 2: Schema Definitions
1. Create StateCategory schema
2. Create WorkflowStateCatalog schema
3. Define field types and descriptions

### Task 3: API Endpoint
1. Implement GET /states/ endpoint
2. Extract state values from all enums
3. Create StateCategory objects for each category
4. Create WorkflowStateCatalog response
5. Return response

### Task 4: Metrics and Logging
1. Implement performance timing
2. Record business event metrics
3. Record HTTP request metrics
4. Implement error logging
5. Handle exceptions gracefully

### Task 5: Testing
1. Test endpoint returns all state categories
2. Test all enum values are included
3. Test response structure
4. Test error handling
5. Performance testing

---

## 11. STATE VALIDATION

### 11.1 State Validation Functions
Helper functions available for state validation:

**get_valid_process_instance_states()**
- Returns list of all valid process instance state values
- Used for validation in other endpoints

**is_valid_process_instance_state(state: str)**
- Checks if string is valid process instance state
- Returns boolean
- Used for input validation

**get_valid_activity_instance_states()**
- Returns list of all valid activity instance state values

**get_valid_user_task_states()**
- Returns list of all valid user task state values

**get_valid_external_task_states()**
- Returns list of all valid external task state values

**get_valid_job_states()**
- Returns list of all valid job state values

**get_valid_case_instance_states()**
- Returns list of all valid case instance state values

### 11.2 Validation Usage
- Used in filter validation
- Used in search query validation
- Used in API parameter validation
- Ensures only valid states are accepted

---

## 12. SUMMARY

This documentation provides a complete business-level guide for implementing the states functionality. Key points to remember:

1. **Read-Only Endpoint**: Single GET endpoint, no database queries
2. **Static Data**: All state definitions from enum classes
3. **Six Categories**: Process instances, activity instances, user tasks, external tasks, jobs, case instances
4. **State Definitions**: Complete list of all possible states in each category
5. **No Filters**: Endpoint accepts no query parameters
6. **Fast Performance**: No database queries, very fast response
7. **Cacheable**: Response is static and can be cached
8. **State Mapping**: Process instance states mapped from database fields
9. **Validation Helpers**: Helper functions available for state validation
10. **Metrics**: Performance and business event tracking

Follow this documentation step-by-step to ensure a complete and correct implementation.
