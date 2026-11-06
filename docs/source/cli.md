# CLI Commands Reference

This document explains all available CLI commands for the application. The CLI is built using Typer and provides commands for running the server, managing database migrations, and viewing configuration.

## Command Structure

All commands are executed using:
```
python manage.py <command> [options]
```

If no command is provided, the application defaults to the `runserver` command.

## Getting Help

To see all available commands and their descriptions:
```
python manage.py --help
```

To get help for a specific command:
```
python manage.py <command> --help
```

To display a detailed help message with command categories and examples:
```
python manage.py help
```

---

## Server Commands

### `runserver`

**Purpose**: Starts the FastAPI application server using uvicorn.

**Usage**:
```
python manage.py runserver
```

**Behavior**:
- Calculates optimal worker count based on CPU cores and configuration
- Configures uvicorn with settings from configuration files
- Enables auto-reload in debug mode (development)
- Uses multiple workers in production mode (if configured)
- Uses single worker in debug mode for easier development

**Worker Calculation Logic**:
- If configured workers is 1, uses 1 worker (development mode)
- Otherwise calculates: `min(configured_workers, max_workers, (CPU_cores * 2) + 1)`
- Formula `(2 * CPU cores) + 1` is a common pattern for async workers
- Ensures at least 1 worker is always used

**Configuration Used**:
- `HOST` - Server bind address
- `PORT` - Server port number
- `DEBUG` - Enables auto-reload and single worker mode
- `LOG_LEVEL` - Logging verbosity
- `uvicorn.WORKERS` - Configured worker count
- `uvicorn.WORKERS_MAX` - Maximum allowed workers
- `uvicorn.TIMEOUT_KEEP_ALIVE` - Keep-alive timeout
- `uvicorn.LIMIT_CONCURRENCY` - Maximum concurrent connections
- `uvicorn.LIMIT_MAX_REQUESTS` - Maximum requests per worker
- `uvicorn.LIMIT_MAX_REQUESTS_JITTER` - Random jitter added to max requests to stagger worker restarts
- `uvicorn.BACKLOG` - Connection backlog size

**When to Use**:
- Starting the application in any environment
- Development with auto-reload
- Production with multiple workers

**Notes**:
- Auto-reload is automatically enabled when `DEBUG=true`
- Multiple workers are only used in production mode (not in debug)
- Server logs use the configured logging system (structured logging)

---

## Migration Commands

All migration commands require the database to be enabled in configuration. If database is disabled, commands will exit with an error.

### `makemigrations`

**Purpose**: Creates a new database migration file using Alembic.

**Usage**:
```
python manage.py makemigrations --message "migration message"
python manage.py makemigrations -m "migration message"
```

**Options**:
- `--message` or `-m` (required): Descriptive message for the migration
- `--autogenerate` or `--no-autogenerate` (optional, default: `true`): Whether to auto-generate migration from model changes

**Behavior**:
- Creates a new migration file in `config/migrations/versions/`
- If autogenerate is enabled, compares current models with database schema and generates migration automatically
- If autogenerate is disabled, creates an empty migration file for manual editing
- Migration file name includes timestamp and message slug

**When to Use**:
- After creating or modifying database models
- When you need to create a custom migration manually
- Before deploying schema changes

**Example Scenarios**:
- Creating a new table: `makemigrations -m "add users table"`
- Adding a column: `makemigrations -m "add email to users"`
- Custom migration: `makemigrations -m "custom data migration" --no-autogenerate`

**Notes**:
- Always review auto-generated migrations before applying
- Migration messages should be descriptive and clear
- Migrations are version-controlled and should be committed with code changes

### `migrate`

**Purpose**: Applies pending database migrations to bring the database schema up to date.

**Usage**:
```
python manage.py migrate
python manage.py migrate --revision head
python manage.py migrate -r head
```

**Options**:
- `--revision` or `-r` (optional, default: `head`): Target revision to migrate to (usually `head` for latest)

**Behavior**:
- Checks current database revision
- Applies all pending migrations in order
- Updates the `alembic_version` table with the new revision
- Runs migrations in a transaction (rolls back on error)

**When to Use**:
- After pulling new code with migration files
- After creating new migrations
- During deployment to update database schema
- To bring database to latest schema version

**Example Scenarios**:
- Apply all pending migrations: `migrate`
- Apply up to specific revision: `migrate -r abc123`
- Deploy to production: Run `migrate` as part of deployment process

**Notes**:
- Always backup database before running migrations in production
- Migrations are applied in order (cannot skip versions)
- Failed migrations leave database in previous state (transaction rollback)

### `downgrade`

**Purpose**: Rolls back database migrations to a previous revision.

**Usage**:
```
python manage.py downgrade --revision <revision>
python manage.py downgrade -r <revision>
```

**Options**:
- `--revision` or `-r` (required): Target revision to downgrade to (revision ID or `base` for all)

**Behavior**:
- Reverses migrations from current revision to target revision
- Runs downgrade operations in reverse order
- Updates the `alembic_version` table
- Can lose data if migrations are not reversible

**When to Use**:
- Rolling back problematic migrations
- Reverting to a previous schema version
- Testing migration rollback procedures
- Development/testing scenarios

**Example Scenarios**:
- Rollback one migration: `downgrade -r <previous_revision>`
- Rollback all migrations: `downgrade -r base`
- Rollback to specific version: `downgrade -r abc123`

**Notes**:
- ⚠️ **Warning**: Downgrading can cause data loss if migrations are not fully reversible
- Always backup database before downgrading
- Some migrations cannot be automatically reversed
- Use with caution in production environments

### `history`

**Purpose**: Displays the complete migration history showing all available revisions.

**Usage**:
```
python manage.py history
```

**Behavior**:
- Lists all migration revisions in chronological order
- Shows revision IDs, branch labels, and migration messages
- Displays the migration chain (which migrations depend on which)
- Indicates current database revision (if connected)

**When to Use**:
- Viewing all available migrations
- Understanding migration sequence
- Finding revision IDs for downgrade/stamp operations
- Debugging migration issues

**Output Format**:
- Shows revision ID, branch, and message for each migration
- Displays migration chain relationships
- May indicate current revision if database is accessible

**Notes**:
- Does not require database connection (reads from migration files)
- Useful for planning migration strategy
- Helps identify which migrations need to be applied

### `show-applied`

**Purpose**: Shows the current database revision (which migrations have been applied).

**Usage**:
```
python manage.py show-applied
```

**Behavior**:
- Connects to the database
- Queries the `alembic_version` table
- Displays the current revision ID
- Shows warning if no migrations have been applied yet

**When to Use**:
- Checking current database schema version
- Verifying migrations were applied successfully
- Debugging migration state
- Before/after migration operations

**Example Scenarios**:
- Verify migration applied: Run after `migrate` to confirm
- Check database state: Before deploying new migrations
- Troubleshooting: When migrations seem stuck

**Notes**:
- Requires database connection
- Shows the revision ID, not the migration message
- Use `history` to see what that revision represents

### `stamp`

**Purpose**: Marks the database as being at a specific revision without running migrations.

**Usage**:
```
python manage.py stamp --revision <revision>
python manage.py stamp -r <revision>
```

**Options**:
- `--revision` or `-r` (required): Revision to stamp the database with

**Behavior**:
- Updates the `alembic_version` table to the specified revision
- Does not run any migration operations
- Useful when database schema matches a revision but version table is out of sync

**When to Use**:
- Database schema already matches a revision (manual changes)
- Syncing version table after manual schema changes
- Marking database as being at a specific point
- Recovery scenarios where schema and version are mismatched

**Example Scenarios**:
- Manual schema changes: After manually applying schema changes, stamp to match
- Recovery: When version table is incorrect but schema is correct
- Initial setup: Stamping base revision before first migration

**Notes**:
- ⚠️ **Warning**: Only use when database schema actually matches the revision
- Does not modify database schema, only version table
- Can cause issues if schema doesn't match the stamped revision
- Use with caution and verify schema matches before stamping

---

## Configuration Commands

### `show-config`

**Purpose**: Displays all configuration settings organized by section.

**Usage**:
```
python manage.py show-config
```

**Behavior**:
- Dynamically discovers all settings from Dynaconf
- Organizes settings into logical sections (Application, Database, Redis, etc.)
- Masks sensitive information (passwords, secrets, keys, tokens)
- Shows which environment is active
- Displays formatted, readable output

**Output Sections**:
- **Application Configuration** - General app settings (debug, log level, host, port)
- **Database Configuration** - Database connection and pool settings
- **Redis Configuration** - Redis connection settings (if enabled)
- **Keycloak Configuration** - Authentication settings (if configured)
- **Uvicorn Configuration** - Server performance settings
- **CORS Configuration** - Cross-origin resource sharing settings
- **Security Configuration** - Security headers and rate limiting
- **Logging Configuration** - File logging settings

**Sensitive Data Masking**:
- Passwords, secrets, keys, tokens, and credentials are automatically masked
- Masked values show as asterisks (`*`)
- Helps prevent accidental exposure of sensitive information

**When to Use**:
- Verifying configuration is loaded correctly
- Debugging configuration issues
- Checking which environment is active
- Reviewing all settings before deployment
- Troubleshooting configuration problems

**Example Output**:
- Shows environment name (development, production, testing)
- Lists all settings organized by section
- Displays formatted values (booleans, lists, strings)
- Masks sensitive fields automatically

**Notes**:
- Safe to run in any environment (sensitive data is masked)
- Useful for configuration verification
- Can be piped to grep for filtering: `show-config | grep DATABASE`
- Shows actual applied values (after environment variable overrides)

### `generate-secret-key`

**Purpose**: Generate a cryptographically secure random secret key for use as `APP_SECRET_KEY` in your `.env` file or environment variables.

**Usage**:
```
python manage.py generate-secret-key [--length/-l <length>]
```

**Options**:
- `--length`, `-l`: Length of the secret key in characters (default: 64, minimum: 32)

**Behavior**:
- Generates a cryptographically secure random key using Python's `secrets` module
- Uses URL-safe base64 encoding (`secrets.token_urlsafe`)
- Ensures minimum length of 32 characters
- Displays the generated key with instructions on how to use it

**Output**:
- Shows the generated secret key
- Provides instructions for adding to `.env` file
- Provides instructions for setting as environment variable

**Examples**:
```
# Generate default 64-character key
python manage.py generate-secret-key

# Generate 128-character key
python manage.py generate-secret-key --length 128

# Generate minimum 32-character key
python manage.py generate-secret-key -l 32
```

**Use Cases**:
- Generate a secure secret key for new projects
- Regenerate secret keys for security rotation
- Create keys of specific lengths for different requirements
- Quick setup for local development

**Security Notes**:
- The generated key is cryptographically secure and suitable for production use
- Minimum recommended length is 32 characters
- Default length of 64 characters provides excellent security
- Never commit generated keys to version control
- Store keys securely in environment variables or secrets managers

---

## Utility Commands

### `help`

**Purpose**: Display a comprehensive help message with all available commands, grouped by category, with usage examples.

**Usage**:
```
python manage.py help
```

**Behavior**:
- Displays all available commands organized by category:
  - Server Commands
  - Database Migration Commands
  - Configuration Commands
  - Utility Commands
- Shows brief descriptions and usage examples for each command
- Provides quick examples for common tasks
- Includes information on how to get more detailed help

**When to Use**:
- When you need a quick reference of all available commands
- When you want to see command categories and examples
- As a starting point for learning the CLI

**Notes**:
- This is a convenience command that provides formatted help
- For detailed information about specific commands, use `python manage.py <command> --help`
- For complete documentation, see `docs/cli.md`

---

## Command Categories Summary

### Server Management
- **`runserver`** - Start the application server

### Database Migrations
- **`makemigrations`** - Create new migration files
- **`migrate`** - Apply pending migrations
- **`downgrade`** - Rollback migrations
- **`history`** - View migration history
- **`show-applied`** - Check current database revision
- **`stamp`** - Mark database at specific revision

### Configuration
- **`show-config`** - Display all configuration settings
- **`generate-secret-key`** - Generate secure secret key for APP_SECRET_KEY

### Utilities
- **`help`** - Display comprehensive help message with all commands

---

## Common Workflows

### Initial Setup Workflow

1. **Create initial migration**:
   ```
   python manage.py makemigrations -m "initial migration"
   ```

2. **Apply migrations**:
   ```
   python manage.py migrate
   ```

3. **Verify migration**:
   ```
   python manage.py show-applied
   ```

4. **Start server**:
   ```
   python manage.py runserver
   ```

### Development Workflow

1. **Make model changes** in your code

2. **Create migration**:
   ```
   python manage.py makemigrations -m "add new field"
   ```

3. **Review migration file** in `config/migrations/versions/`

4. **Apply migration**:
   ```
   python manage.py migrate
   ```

5. **Verify**:
   ```
   python manage.py show-applied
   ```

### Deployment Workflow

1. **Check current revision**:
   ```
   python manage.py show-applied
   ```

2. **View pending migrations**:
   ```
   python manage.py history
   ```

3. **Apply migrations**:
   ```
   python manage.py migrate
   ```

4. **Verify configuration**:
   ```
   python manage.py show-config
   ```

5. **Start server**:
   ```
   python manage.py runserver
   ```

### Troubleshooting Workflow

1. **Check configuration**:
   ```
   python manage.py show-config
   ```

2. **View migration history**:
   ```
   python manage.py history
   ```

3. **Check current revision**:
   ```
   python manage.py show-applied
   ```

4. **If needed, rollback**:
   ```
   python manage.py downgrade -r <previous_revision>
   ```

---

## Error Handling

### Database Not Enabled

If database is disabled in configuration, migration commands will exit with:
```
[ERROR] Database is not enabled in settings
```

**Solution**: Enable database in configuration (`APP_DATABASE__ENABLED=true`) or `settings.toml`.

### Migration Errors

If migrations fail:
- Database is rolled back to previous state
- Error message indicates which migration failed
- Check migration files and database state
- Review logs for detailed error information

### Configuration Errors

If configuration is invalid:
- Application startup will fail
- `show-config` may show errors
- Check validators in `config/settings/validators.py`
- Verify environment variables and TOML files

---

## Docker Usage

All CLI commands work the same way in Docker containers:

```
# Run migrations in container
docker compose exec app python manage.py migrate

# Show configuration in container
docker compose exec app python manage.py show-config

# View migration history in container
docker compose exec app python manage.py history
```

The commands behave identically whether run directly or in a container.

---

## Best Practices

1. **Always Review Migrations**: Check auto-generated migrations before applying
2. **Backup Before Migrations**: Always backup database before running migrations in production
3. **Test Migrations**: Test migrations in development/staging before production
4. **Use Descriptive Messages**: Write clear migration messages
5. **Verify Configuration**: Use `show-config` to verify settings before deployment
6. **Check Migration State**: Use `show-applied` to verify migrations were applied
7. **Version Control**: Commit migration files with code changes
8. **Never Skip Migrations**: Apply migrations in order, don't skip versions

---

## Additional Notes

- **Default Command**: Running `python manage.py` without arguments defaults to `runserver`
- **Help System**: All commands support `--help` for detailed usage information
- **Error Messages**: Commands provide clear error messages with actionable guidance
- **Exit Codes**: Commands exit with appropriate codes (0 for success, non-zero for errors)
- **Logging**: Server command uses configured logging system
- **Configuration Priority**: Commands respect configuration priority (env vars > .env > TOML)
