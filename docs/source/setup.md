# Project Setup and Architecture

This document explains how the project is structured and how all components work together. It focuses on the logical flow and architecture rather than code implementation.

## Overview

The project follows a multi-app architecture pattern where the application is composed of multiple independent modules (apps) that are automatically discovered and integrated. Each app can have its own models, schemas, services, and routes, while sharing common infrastructure through the core package.

## Project Structure

The project is organized into several key directories:

### Application Directory (`apps/`)

The `apps/` directory contains all application modules. Each subdirectory represents a separate feature or domain:

- **`apps/common/`** - Common endpoints and utilities (health checks, version info, root endpoint)
- **`apps/core/`** - Core infrastructure shared across all apps (database, exceptions, middleware, app factory)
- **`apps/{app_name}/`** - Individual feature apps (users, orders, etc.)

Each app follows a layered architecture:
- **`models/`** - Database models (SQLAlchemy)
- **`schemas/`** - Request/response schemas (Pydantic)
- **`services/`** - Business logic orchestration
- **`repository/`** - Data access layer (DAL for reads, BLL for writes)
- **`routers/`** - API route handlers (FastAPI)
- **`tests/`** - Test files
- **`helpers/`** - App-specific utilities (enums, exceptions)
- **`types.py`** - Type aliases for the app

### Configuration Directory (`config/`)

Contains all configuration-related files:

- **`config/settings/`** - Dynaconf configuration files (TOML format)
- **`config/logging/`** - Logging configuration and setup
- **`config/metrics/`** - Prometheus metrics setup
- **`config/migrations/`** - Alembic database migration files

### Root Files

- **`manage.py`** - Application entry point and CLI command handler
- **`alembic.ini`** - Alembic configuration for database migrations
- **`.env`** - Environment variables (not in version control)

## Application Initialization Flow

When the application starts, it follows a specific sequence:

### 1. Entry Point (`manage.py`)

The `manage.py` file serves dual purposes:
- **CLI Command Handler** - Provides commands for running the server, migrations, and configuration
- **Application Entry Point** - Creates and runs the FastAPI application

When executed, it first calculates the optimal number of workers based on CPU count and configuration settings. This calculation considers the configured worker count, maximum allowed workers, and system CPU cores using a formula that balances performance and resource usage.

### 2. Application Factory (`apps/core/app_factory.py`)

The `create_app()` function is responsible for building the complete FastAPI application. It follows this sequence:

**Step 1: Create FastAPI Instance**
- Creates a FastAPI application with metadata (title, description, version)
- Sets up OpenAPI documentation URLs (only in debug mode)
- Configures the default response class to use ORJSON for better performance
- Attaches a lifespan context manager for startup and shutdown events

**Step 2: Register Middleware**
- Registers all middleware in a specific order (important for execution sequence)
- Middleware handles: security headers, CORS, request size limits, rate limiting, logging, timing
- Each middleware processes requests before they reach route handlers and responses before they're sent

**Step 3: Register Exception Handlers**
- Registers centralized exception handlers for consistent error responses
- Handles custom exceptions, validation errors, database errors, and general exceptions
- Converts all exceptions to standardized JSON error responses

**Step 4: Load Application Routers**
- Automatically discovers and loads routers from all apps in the `apps/` directory
- Uses dynamic import to find routers in each app directory
- Mounts each router with a prefix matching the app name

**Step 5: Customize OpenAPI Schema**
- Creates a custom OpenAPI schema generator
- Ensures the schema is generated correctly with all discovered routes

### 3. Lifespan Events

The application uses FastAPI's lifespan context manager to handle startup and shutdown:

**Startup Sequence:**
1. Initialize logging system (structured logging with environment-aware formatting)
2. Setup Prometheus metrics collection
3. Initialize database connection manager (if database is enabled)
4. Store database manager in application state for access throughout request lifecycle
5. Display startup information (pretty banner in development, structured logs in production)
6. Log system information (CPU, memory, workers, database pool configuration)

**Shutdown Sequence:**
1. Log shutdown initiation
2. Close database connections gracefully
3. Clean up application state
4. Log shutdown completion

## Configuration System

The project uses Dynaconf for configuration management with a hierarchical priority system:

### Configuration Priority (Highest to Lowest)

1. **Environment Variables** - OS-level environment variables with `APP_` prefix
2. **`.env` File** - Local environment file with `APP_` prefix
3. **Environment-Specific TOML** - Files like `settings.production.toml` or `settings.development.toml`
4. **Base Settings TOML** - `settings.toml` with default values

### Configuration Structure

Settings are organized into logical sections:
- **Application Settings** - General app configuration (debug, log level, host, port)
- **Database Settings** - Database connection and pool configuration
- **Redis Settings** - Cache configuration (if enabled)
- **Keycloak Settings** - Authentication configuration (if enabled)
- **Uvicorn Settings** - Server performance tuning
- **CORS Settings** - Cross-origin resource sharing configuration

### Environment Detection

The system automatically detects the environment from the `ENV` environment variable. If not set, it defaults to `development`. Each environment can have its own settings file that overrides base settings.

## Multi-App Architecture and Router Discovery

The project uses automatic router discovery to enable a modular architecture:

### Discovery Process

1. **Common App First** - The `apps/common` router is always loaded first (if it exists)
2. **Directory Scanning** - The system scans all directories in `apps/`
3. **Filtering** - Skips directories that:
   - Start with underscore (private)
   - Are named `common` (already handled)
   - Are named `core` (infrastructure, not an app)
4. **Router Import Attempts** - For each valid app directory, tries to import router from:
   - `apps.{app_name}.routers.router` (new layered structure)
   - `apps.{app_name}.routers` (legacy structure)
   - `apps.{app_name}.api` (legacy structure)
5. **Router Registration** - If a router is found, it's registered with:
   - Prefix: `/{app_name}` (e.g., `/users`, `/orders`)
   - Tags: `[app_name]` (for OpenAPI grouping)

### Benefits

- **Modularity** - Each app is self-contained
- **Automatic Integration** - New apps are automatically available without manual registration
- **Flexibility** - Apps can follow different structures (backward compatible)
- **Isolation** - Apps don't need to know about each other

## Middleware System

Middleware is registered in a specific order to ensure proper request/response processing:

### Middleware Execution Order

1. **Security Headers Middleware** - Adds security headers (CSP, HSTS, X-Frame-Options, etc.)
2. **CORS Middleware** - Handles cross-origin requests
3. **Request Size Limit Middleware** - Prevents large request attacks
4. **Rate Limiting Middleware** - Enforces rate limits per client
5. **Logging Middleware** - Logs all requests with context (request ID, method, path)
6. **Timing Middleware** - Adds timing headers to responses

### Request Flow Through Middleware

When a request arrives:
1. Each middleware processes the request in registration order
2. Middleware can modify the request or add data to request state
3. Request reaches the route handler
4. Response flows back through middleware in reverse order
5. Each middleware can modify the response or add headers

## Database Connection Management

The database system uses a connection pool pattern for efficient resource management:

### Database Manager Initialization

1. **Configuration Check** - Verifies database is enabled in settings
2. **Connection String Construction** - Builds database URL from settings
3. **Engine Creation** - Creates SQLAlchemy async engine with:
   - Connection pool configuration (size, max overflow)
   - Connection timeout settings
   - Pool pre-ping (checks connections before use)
4. **Session Factory** - Creates async session factory for dependency injection

### Connection Pool Logic

- **Pool Size** - Number of connections maintained in the pool
- **Max Overflow** - Additional connections allowed beyond pool size
- **Total Capacity** - Pool size + max overflow = maximum concurrent connections
- **Connection Lifecycle** - Connections are checked before use and recycled after use

### Session Management

- **Dependency Injection** - Database sessions are provided via FastAPI dependencies
- **Automatic Cleanup** - Sessions are automatically closed after request completion
- **Transaction Management** - Transactions are managed at the BLL (Business Logic Layer) level

## CLI Command System

The CLI uses Typer for command definition and provides several categories of commands:

### Server Commands

- **`runserver`** - Starts the FastAPI server with uvicorn
  - Calculates optimal worker count
  - Configures uvicorn with settings
  - Enables auto-reload in debug mode
  - Uses multiple workers in production (if configured)

### Migration Commands

- **`makemigrations`** - Creates new database migration files
  - Uses Alembic for migration generation
  - Can auto-generate from model changes or create empty migrations
- **`migrate`** - Applies pending migrations to the database
- **`downgrade`** - Rolls back to a specific migration revision
- **`history`** - Shows all migration revisions
- **`show-applied`** - Shows current database revision
- **`stamp`** - Marks database as being at a revision without running migrations

### Configuration Commands

- **`show-config`** - Displays all configuration settings
  - Dynamically discovers all settings from Dynaconf
  - Organizes settings into logical sections
  - Masks sensitive information (passwords, secrets)
  - Shows which environment is active

## Request Lifecycle

Understanding how a request flows through the system:

### 1. Request Arrival

- Request arrives at the uvicorn server
- Server creates a request object with headers, body, query parameters

### 2. Middleware Processing

- Request flows through all registered middleware
- Each middleware can:
  - Add data to request state
  - Modify request headers
  - Reject requests (rate limiting, size limits)
  - Add logging context

### 3. Route Matching

- FastAPI matches the request path to a registered route
- Extracts path parameters and query parameters
- Validates request body against Pydantic schemas

### 4. Dependency Injection

- FastAPI resolves all dependencies (database session, request object, etc.)
- Dependencies are created in order and can depend on each other
- Database session is created from the connection pool

### 5. Route Handler Execution

- Route handler function is called with injected dependencies
- Handler calls service layer functions
- Service layer orchestrates business logic
- Service calls repository layer (BLL/DAL) for data operations

### 6. Response Generation

- Route handler returns a response (Pydantic model or ORJSONResponse)
- FastAPI serializes the response to JSON
- Response flows back through middleware (reverse order)
- Middleware can add headers or modify response

### 7. Response Delivery

- Final response is sent to the client
- Database session is closed and returned to pool
- Request context is cleaned up

## Worker Management

The application supports multiple worker processes for handling concurrent requests:

### Worker Calculation Logic

1. **Check Configuration** - Reads configured worker count from settings
2. **Single Worker Mode** - If configured to 1, uses single worker (development mode)
3. **Optimal Calculation** - Calculates optimal workers using formula: `min(configured, max_allowed, (CPU_cores * 2) + 1)`
4. **Minimum Guarantee** - Ensures at least 1 worker is used

### Worker Behavior

- **Development Mode** - Always uses single worker with auto-reload
- **Production Mode** - Uses calculated worker count (if > 1)
- **Worker Isolation** - Each worker has its own database connection pool
- **Load Distribution** - Uvicorn distributes requests across workers

## Logging System

The logging system provides structured, environment-aware logging:

### Logging Initialization

1. **Environment Detection** - Determines if running in development or production
2. **Formatter Selection**:
   - **Development** - Pretty, colorful console output for readability
   - **Production** - JSON output compatible with log aggregation systems (Elasticsearch)
3. **Logger Configuration** - Sets up log levels, handlers, and formatters

### Logging Features

- **Structured Logging** - All logs include context (request ID, method, path, user ID)
- **Automatic Context** - Middleware automatically adds request context to all logs
- **Third-party Integration** - Formats logs from uvicorn, FastAPI, SQLAlchemy
- **Log Levels** - Configurable via environment variable (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Metrics Collection

The application includes Prometheus metrics for monitoring:

### Metrics Setup

- **Initialization** - Metrics are set up during application startup
- **Endpoint** - Metrics are exposed at `/metrics` endpoint (if enabled)
- **Automatic Collection** - Request counts, durations, and error rates are automatically tracked
- **Custom Metrics** - Applications can add custom metrics for business logic

## Error Handling

The application uses a centralized exception handling system:

### Exception Hierarchy

- **BaseAPIException** - Base class for all API exceptions
- **App-Specific Exceptions** - Each app can define its own exception hierarchy
- **Standard Exceptions** - Common exceptions (NotFoundError, ValidationError, etc.)

### Exception Flow

1. **Exception Raised** - Route handler or service raises an exception
2. **Exception Handler** - Centralized handler catches the exception
3. **Response Generation** - Handler converts exception to standardized JSON response
4. **Logging** - Exception is logged with full context
5. **Client Response** - Error response is sent to client

## Development vs Production Differences

The application behaves differently based on the environment:

### Development Mode

- **Debug Enabled** - Detailed error messages, stack traces
- **Auto-Reload** - Server restarts on code changes
- **Pretty Logging** - Colorful console output
- **OpenAPI Docs** - Swagger UI and ReDoc available
- **Single Worker** - Easier debugging
- **Debug Endpoints** - Additional health check endpoints available

### Production Mode

- **Debug Disabled** - Generic error messages (no stack traces)
- **Structured Logging** - JSON logs for log aggregation
- **Multiple Workers** - Better performance and concurrency
- **No OpenAPI Docs** - Documentation endpoints disabled
- **Optimized Settings** - Production-tuned timeouts and limits

## Docker Integration

When running in Docker, additional logic applies:

### Entrypoint Script

The entrypoint script handles container initialization:

1. **Database Wait** - Waits for database to be ready before starting app
2. **Auto-Migration** - Optionally runs database migrations on startup
3. **Service Name Resolution** - Automatically fixes `localhost` to service names in Docker networks
4. **Graceful Shutdown** - Handles container stop signals properly

### Docker Compose

- **Service Dependencies** - App service depends on database service
- **Health Checks** - Services have health check configurations
- **Network Isolation** - Services communicate via Docker network
- **Volume Mounts** - Code can be mounted for development

## Summary

The project setup follows these key principles:

1. **Modularity** - Multi-app architecture allows independent feature development
2. **Automatic Discovery** - Routers and apps are automatically discovered and integrated
3. **Configuration Hierarchy** - Flexible configuration with environment-specific overrides
4. **Resource Management** - Efficient database connection pooling and worker management
5. **Observability** - Comprehensive logging and metrics for production monitoring
6. **Developer Experience** - Auto-reload, pretty logging, and debug tools in development
7. **Production Ready** - Optimized settings, structured logging, and health checks for production

This architecture enables teams to build scalable microservices while maintaining code organization, type safety, and operational excellence.
