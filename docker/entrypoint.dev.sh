#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to wait for database to be ready
wait_for_db() {
    if [ "${APP_DATABASE__ENABLED}" != "true" ]; then
        print_info "Database is disabled, skipping database wait"
        return 0
    fi

    print_info "Waiting for database to be ready..."

    DB_HOST="${APP_DATABASE__HOST:-postgres}"
    DB_PORT="${APP_DATABASE__PORT:-5432}"
    DB_USER="${APP_DATABASE__USER:-postgres}"
    DB_NAME="${APP_DATABASE__NAME:-app_db}"
    DB_PASSWORD="${APP_DATABASE__PASSWORD:-postgres}"

    # Auto-fix: If running in Docker and host is localhost, use service name instead
    if [ -f /.dockerenv ] && [ "$DB_HOST" = "localhost" ]; then
        print_error "=========================================="
        print_error "CRITICAL CONFIGURATION ERROR DETECTED"
        print_error "=========================================="
        print_error "Running in Docker but database host is set to 'localhost'"
        print_error ""
        print_error "In Docker Compose, 'localhost' refers to the container itself,"
        print_error "not other services. You must use the service name instead."
        print_error ""
        print_error "Current configuration:"
        print_error "  APP_DATABASE__HOST=localhost  [WRONG]"
        print_error ""
        print_error "Required configuration:"
        print_error "  APP_DATABASE__HOST=postgres  [CORRECT]"
        print_error ""
        print_error "Auto-fixing by using service name 'postgres'..."
        DB_HOST="postgres"
        # Export the corrected value so Python processes can see it
        export APP_DATABASE__HOST="postgres"
        print_info "[OK] Changed database host from 'localhost' to 'postgres'"
        print_info "[OK] Exported APP_DATABASE__HOST=postgres for Python processes"
        print_info ""
        print_warn "NOTE: To make this permanent, update your configuration:"
        print_warn "  - Set APP_DATABASE__HOST=postgres in your .env file"
        print_warn "  - Or remove APP_DATABASE__HOST from .env to use docker-compose.yml default"
        print_warn ""
    fi

    # Display connection details
    print_info "Database connection details:"
    print_info "  Host: $DB_HOST"
    print_info "  Port: $DB_PORT"
    print_info "  User: $DB_USER"
    print_info "  Database: $DB_NAME"
    print_info "  Password: ${DB_PASSWORD:0:3}*** (hidden)"

    MAX_RETRIES=30
    RETRY_COUNT=0

    # Step 1: Check if we can resolve the hostname
    print_info "Step 1: Checking hostname resolution..."
    if ! getent hosts "$DB_HOST" > /dev/null 2>&1 && ! ping -c 1 -W 2 "$DB_HOST" > /dev/null 2>&1; then
        print_warn "Warning: Cannot resolve hostname '$DB_HOST'. This might be normal if DNS is not fully ready."
    else
        print_info "[OK] Hostname '$DB_HOST' is resolvable"
    fi

    # Step 2: Check if we can reach the port
    print_info "Step 2: Checking port connectivity..."
    if command -v nc > /dev/null 2>&1; then
        if nc -z -w 2 "$DB_HOST" "$DB_PORT" 2>/dev/null; then
            print_info "[OK] Port $DB_PORT is reachable on $DB_HOST"
        else
            print_warn "[WARN] Port $DB_PORT is not reachable on $DB_HOST"
            if [ "$DB_HOST" = "localhost" ] && [ -f /.dockerenv ]; then
                print_error "  [ERROR] This is expected! In Docker, 'localhost' refers to the container itself, not other services."
                print_error "     Use the Docker Compose service name (e.g., 'postgres') instead."
            fi
        fi
    else
        print_warn "[WARN] 'nc' (netcat) not available, skipping port check"
    fi

    # Step 3: Wait for database to be ready using pg_isready
    print_info "Step 3: Waiting for PostgreSQL to accept connections..."

    LAST_ERROR=""
    until [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
        RETRY_COUNT=$((RETRY_COUNT + 1))

        # Try pg_isready with error capture
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /tmp/pg_isready_output.txt 2>&1; then
            print_info "[OK] Database is ready!"

            # Verify we can actually connect with psql
            print_info "Step 4: Verifying database connection..."
            export PGPASSWORD="$DB_PASSWORD"
            if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
                print_info "[OK] Database connection verified successfully"
                unset PGPASSWORD
                return 0
            else
                print_warn "[WARN] pg_isready passed but psql connection failed"
                print_warn "  This might indicate authentication issues"
                LAST_ERROR="Connection verification failed"
            fi
            unset PGPASSWORD
        else
            # Capture error for display
            if [ -f /tmp/pg_isready_output.txt ]; then
                LAST_ERROR=$(cat /tmp/pg_isready_output.txt 2>/dev/null || echo "Unknown error")
            fi

            if [ $((RETRY_COUNT % 5)) -eq 0 ]; then
                # Show detailed error every 5 attempts
                print_warn "Database not ready (attempt ${RETRY_COUNT}/${MAX_RETRIES})"
                print_warn "  Last error: ${LAST_ERROR}"
                print_warn "  Testing connectivity..."

                # Additional diagnostics
                if command -v nc > /dev/null 2>&1; then
                    if nc -z -w 2 "$DB_HOST" "$DB_PORT" 2>/dev/null; then
                        print_info "  [OK] Port is open"
                    else
                        print_error "  [ERROR] Port is closed or unreachable"
                    fi
                fi
            else
                print_info "Database not ready yet. Waiting... (${RETRY_COUNT}/${MAX_RETRIES})"
            fi
        fi

        sleep 2
    done

    # Final diagnostics on failure
    print_error "=========================================="
    print_error "Database connection failed after ${MAX_RETRIES} attempts"
    print_error "=========================================="
    print_error "Connection details used:"
    print_error "  Host: $DB_HOST"
    print_error "  Port: $DB_PORT"
    print_error "  User: $DB_USER"
    print_error "  Database: $DB_NAME"
    print_error ""
    print_error "Last pg_isready error:"
    if [ -f /tmp/pg_isready_output.txt ]; then
        cat /tmp/pg_isready_output.txt | sed 's/^/  /' >&2
    else
        print_error "  (No error output captured)"
    fi
    print_error ""
    print_error "Diagnostic information:"

    # Network diagnostics
    if command -v nc > /dev/null 2>&1; then
        print_error "  Testing port connectivity..."
        if nc -z -w 2 "$DB_HOST" "$DB_PORT" 2>/dev/null; then
            print_error "  [OK] Port $DB_PORT is reachable"
        else
            print_error "  [ERROR] Port $DB_PORT is NOT reachable"
            print_error "     Possible causes:"
            if [ "$DB_HOST" = "localhost" ] && [ -f /.dockerenv ]; then
                print_error "     [CRITICAL] Using 'localhost' in Docker Compose!"
                print_error "        In Docker, 'localhost' refers to the container itself, not other services."
                print_error "        SOLUTION: Set APP_DATABASE__HOST=postgres (use the service name)"
                print_error "        Or update your docker-compose.yml to use the service name"
            else
                print_error "     - Database container is not running"
                print_error "     - Network connectivity issue"
                print_error "     - Wrong host/port configuration"
            fi
        fi
    fi

    # DNS resolution
    print_error "  Testing hostname resolution..."
    if getent hosts "$DB_HOST" > /dev/null 2>&1; then
        RESOLVED_IP=$(getent hosts "$DB_HOST" | awk '{print $1}' | head -1)
        print_error "  [OK] Hostname resolves to: $RESOLVED_IP"
    else
        print_error "  [ERROR] Hostname '$DB_HOST' does not resolve"
        print_error "     Possible causes:"
        print_error "     - DNS not configured correctly"
        print_error "     - Docker network issue"
        print_error "     - Wrong hostname in configuration"
    fi

    # Check if postgres service exists in docker-compose
    print_error ""
    print_error "Troubleshooting tips:"
    print_error "  1. Verify the postgres service is running: docker-compose ps"
    print_error "  2. Check postgres logs: docker-compose logs postgres"
    print_error "  3. Verify network connectivity: docker-compose exec app ping $DB_HOST"
    print_error "  4. Check environment variables are set correctly"
    print_error "  5. Ensure APP_DATABASE__ENABLED=true is set"
    print_error "=========================================="

    exit 1
}

# Function to run database migrations
run_migrations() {
    if [ "${APP_DATABASE__ENABLED}" != "true" ]; then
        print_info "Database is disabled, skipping migrations"
        return 0
    fi

    print_info "Running database migrations..."

    # Check if migrations directory exists
    if [ ! -d "config/migrations/versions" ]; then
        print_warn "Migrations directory not found. Skipping migrations."
        return 0
    fi

    # Run migrations
    if python manage.py migrate; then
        print_info "Migrations completed successfully"
    else
        print_error "Migration failed"
        exit 1
    fi
}

# Function to check if we should run migrations
should_run_migrations() {
    # Run migrations if AUTO_MIGRATE is set to true, or if not set (default behavior)
    if [ "${AUTO_MIGRATE:-true}" = "true" ]; then
        return 0
    fi
    return 1
}

# Main execution
main() {
    print_info "Starting application entrypoint..."

    # Wait for database if enabled
    wait_for_db

    # Execute the command passed to the container
    print_info "Starting application..."
    exec "$@"
}

# Trap SIGTERM and SIGINT to handle graceful shutdown
trap 'print_info "Received shutdown signal, exiting..."; exit 0' SIGTERM SIGINT

# Run main function with all arguments
main "$@"
