# Up and Running Guide

This guide covers running the Microservices FastAPI Template with and without Docker.

## Quick Start

### Without Docker

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate      # Windows

# Run the application
python manage.py runserver
```

### With Docker

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f app
```

The application will be available at `http://localhost:8000`

---

## Running Without Docker

### Development Mode

**Start the application:**
```bash
python manage.py runserver
```

**With auto-reload (development):**
```bash
# Set DEBUG=true in .env
export APP_DEBUG=true
python manage.py runserver
```

**Custom host and port:**
```bash
export APP_HOST=127.0.0.1
export APP_PORT=8080
python manage.py runserver
```

### Production Mode

**Set production environment:**
```bash
export ENV=production
export APP_DEBUG=false
export APP_LOG_LEVEL=INFO
python manage.py runserver
```

**Using uvicorn directly:**
```bash
uvicorn manage:app --host 0.0.0.0 --port 8000 --workers 4
```

### Running with Different Environments

**Development:**
```bash
export ENV=development
python manage.py runserver
```

**Production:**
```bash
export ENV=production
python manage.py runserver
```

**Testing:**
```bash
export ENV=testing
python manage.py runserver
```

### CLI Commands

**Show all available commands:**
```bash
python manage.py --help
```

**Database migrations:**
```bash
# Create migration
python manage.py makemigrations -m "migration message"

# Apply migrations
python manage.py migrate

# Show migration history
python manage.py history

# Show current revision
python manage.py show-applied

# Downgrade to specific revision
python manage.py downgrade -r <revision>
```

**Configuration:**
```bash
# Show all configuration
python manage.py show-config

# Show specific setting
python manage.py show-config | grep DATABASE
```

---

## Running With Docker

### Starting Services

**Start all services (detached mode):**
```bash
docker compose up -d
```

**Start with logs visible:**
```bash
docker compose up
```

**Start specific service:**
```bash
docker compose up postgres  # Start only database
docker compose up app       # Start only application
```

### Stopping Services

**Stop all services:**
```bash
docker compose down
```

**Stop and remove volumes (⚠️ deletes data):**
```bash
docker compose down -v
```

**Stop specific service:**
```bash
docker compose stop app
```

### Viewing Logs

**View all logs:**
```bash
docker compose logs
```

**View application logs:**
```bash
docker compose logs app
```

**Follow logs (real-time):**
```bash
docker compose logs -f app
```

**View last 100 lines:**
```bash
docker compose logs --tail=100 app
```

### Executing Commands in Container

**Run CLI commands:**
```bash
# Run migrations
docker compose exec app python manage.py migrate

# Show configuration
docker compose exec app python manage.py show-config

# Access Python shell
docker compose exec app python
```

**Access database:**
```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d app_db

# Run SQL queries
docker compose exec postgres psql -U postgres -d app_db -c "SELECT version();"
```

### Rebuilding Containers

**Rebuild after code changes:**
```bash
docker compose build app
docker compose up -d app
```

**Rebuild without cache:**
```bash
docker compose build --no-cache app
docker compose up -d app
```

**Rebuild all services:**
```bash
docker compose build
docker compose up -d
```

### Environment-Specific Docker Compose

**Development:**
```bash
# Uses docker-compose.yml with ENV=development
export ENV=development
docker compose up -d
```

**Production:**
```bash
# Uses docker-compose.yml with ENV=production
export ENV=production
docker compose up -d
```

**Custom environment file:**
```bash
docker compose --env-file .env.production up -d
```

---

## Verifying the Application

### Health Checks

**Basic health check:**
```bash
curl http://localhost:8000/health
```

**Liveness probe (Kubernetes):**
```bash
curl http://localhost:8000/live
```

**Readiness probe (Kubernetes):**
```bash
curl http://localhost:8000/ready
```

**Version information:**
```bash
curl http://localhost:8000/version
```

### API Documentation

**Swagger UI (development only):**
```
http://localhost:8000/docs
```

**ReDoc (development only):**
```
http://localhost:8000/redoc
```

**OpenAPI Schema:**
```bash
curl http://localhost:8000/openapi.json
```

### Database Health (If Enabled)

**Check database connection:**
```bash
curl http://localhost:8000/health/db
```

**With Docker:**
```bash
docker compose exec app curl http://localhost:8000/health/db
```

---

## Common Workflows

### Development Workflow (Without Docker)

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Set development environment
export ENV=development
export APP_DEBUG=true

# 3. Start application with auto-reload
python manage.py runserver

# 4. In another terminal, run tests
pytest

# 5. Make code changes (auto-reload will restart server)
```

### Development Workflow (With Docker)

```bash
# 1. Start services
docker compose up -d

# 2. View logs
docker compose logs -f app

# 3. Make code changes

# 4. Rebuild and restart
docker compose build app
docker compose restart app

# 5. Run tests in container
docker compose exec app pytest
```

### Database Migration Workflow

**Without Docker:**
```bash
# 1. Create migration
python manage.py makemigrations -m "add users table"

# 2. Review migration file
cat config/migrations/versions/xxxx_add_users_table.py

# 3. Apply migration
python manage.py migrate

# 4. Verify
python manage.py show-applied
```

**With Docker:**
```bash
# 1. Create migration
docker compose exec app python manage.py makemigrations -m "add users table"

# 2. Apply migration (or wait for auto-migration on restart)
docker compose exec app python manage.py migrate

# 3. Verify
docker compose exec app python manage.py show-applied
```

### Production Deployment Workflow

**Without Docker:**
```bash
# 1. Set production environment
export ENV=production
export APP_DEBUG=false
export APP_LOG_LEVEL=INFO

# 2. Run migrations
python manage.py migrate

# 3. Start with multiple workers
uvicorn manage:app --host 0.0.0.0 --port 8000 --workers 4
```

**With Docker:**
```bash
# 1. Set production environment in .env
echo "ENV=production" >> .env
echo "APP_DEBUG=false" >> .env

# 2. Build production image
docker compose build app

# 3. Start services
docker compose up -d

# 4. Verify health
curl http://localhost:8000/health
```

---

## Performance Tuning

### Without Docker

**Adjust worker count:**
```bash
# Set in .env or environment
export APP_UVICORN__WORKERS=4
export APP_UVICORN__WORKERS_MAX=8

python manage.py runserver
```

**Optimize database pool:**
```bash
# In .env
APP_DATABASE__POOL_SIZE=10
APP_DATABASE__MAX_OVERFLOW=20
```

### With Docker

**Set resource limits:**
```yaml
# In docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

**Scale application:**
```bash
# Run multiple instances
docker compose up -d --scale app=3
```

---

## Monitoring and Debugging

### Application Logs

**Without Docker:**
- Logs appear in console (development and production)

**With Docker:**
```bash
# View logs
docker compose logs app

# Follow logs
docker compose logs -f app

# View last 50 lines
docker compose logs --tail=50 app
```

### Metrics Endpoint

**Prometheus metrics (if enabled):**
```bash
curl http://localhost:8000/metrics
```

### Debug Mode

**Enable debug mode:**
```bash
# Without Docker
export APP_DEBUG=true
python manage.py runserver

# With Docker
# Set in .env: APP_DEBUG=true
docker compose up -d
```

**Debug toolbar (development only):**
- Available at `/debug` when `APP_DEBUG=true`
- Shows request/response details, SQL queries, etc.

---

## Troubleshooting

### Application Won't Start

**Check logs:**
```bash
# Without Docker
python manage.py runserver  # Check console output

# With Docker
docker compose logs app
```

**Verify configuration:**
```bash
python manage.py show-config
```

**Check port availability:**
```bash
# Linux/macOS
lsof -i :8000

# Windows
netstat -ano | findstr :8000
```

### Database Connection Issues

**Without Docker:**
```bash
# Test connection
psql -U postgres -h localhost -d app_db

# Check settings
python manage.py show-config | grep DATABASE
```

**With Docker:**
```bash
# Check database container
docker compose ps postgres

# Test connection from app container
docker compose exec app python -c "from apps.core.db import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().check_health())"

# Check database logs
docker compose logs postgres
```

### Migration Issues

**Reset migrations (⚠️ deletes data):**
```bash
# Without Docker
python manage.py downgrade -r base
python manage.py migrate

# With Docker
docker compose exec app python manage.py downgrade -r base
docker compose exec app python manage.py migrate
```

**Check migration status:**
```bash
python manage.py show-applied
python manage.py history
```

### Container Issues

**Restart containers:**
```bash
docker compose restart app
docker compose restart postgres
```

**Rebuild containers:**
```bash
docker compose build --no-cache
docker compose up -d
```

**Remove and recreate:**
```bash
docker compose down
docker compose up -d
```

---

## Next Steps

- **API Documentation**: Visit `http://localhost:8000/docs` (development mode)
- **Add New Apps**: See [README.md](../README.md#adding-new-apps)
- **Database Models**: See [README.md](../README.md#creating-database-models)
- **Configuration**: See [README.md](../README.md#configuration)

---

## Additional Resources

- [Installation Guide](./installation.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
