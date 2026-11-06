# Installation Guide

This guide covers installing the Microservices FastAPI Template with and without Docker.

## Prerequisites

### System Requirements

- **Python**: >= 3.12
- **PostgreSQL**: >= 16 (optional, for database features)
- **Redis**: >= 7.0 (optional, for caching)
- **Docker**: >= 24.0 (optional, for Docker setup)
- **Docker Compose**: >= 2.0 (optional, for Docker setup)

### Operating System

- Linux (Ubuntu 20.04+, Debian 11+, etc.)
- macOS (10.15+)
- Windows (10/11 with WSL2 recommended)

---

## Installation Without Docker

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd microservices-fastapi-template
```

### Step 2: Create Virtual Environment

**On Linux/macOS:**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

**On Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Verify Python version:**
```bash
python --version  # Should be 3.12 or higher
```

### Step 3: Install Dependencies

**Using pip (recommended):**
```bash
pip install --upgrade pip
pip install -r requirements/prod.txt
```

**Using Poetry (alternative):**
```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
```

### Step 4: Install Development Dependencies (Optional)

For development work, install additional tools:
```bash
pip install -r requirements/dev.txt
```

### Step 5: Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp envs/env.dev .env  # Or create manually
```

Edit `.env` and configure your settings:

```bash
# Application Settings
APP_SECRET_KEY=your-secret-key-here-minimum-32-characters-long
APP_DEBUG=true
APP_LOG_LEVEL=INFO
APP_HOST=0.0.0.0
APP_PORT=8000
APP_ENABLE_METRICS=true

# Database Configuration (Optional)
APP_DATABASE__ENABLED=true
APP_DATABASE__DRIVER=postgresql+asyncpg
APP_DATABASE__HOST=localhost
APP_DATABASE__PORT=5432
APP_DATABASE__NAME=app_db
APP_DATABASE__USER=postgres
APP_DATABASE__PASSWORD=postgres
APP_DATABASE__POOL_SIZE=5
APP_DATABASE__MAX_OVERFLOW=10

# Redis Configuration (Optional)
APP_REDIS__ENABLED=false
APP_REDIS__HOST=localhost
APP_REDIS__PORT=6379
APP_REDIS__DB=0

# Keycloak Configuration (Optional)
APP_KEYCLOAK__SERVER_URL=http://localhost:8080
APP_KEYCLOAK__REALM=master
APP_KEYCLOAK__CLIENT_ID=your-client-id
APP_KEYCLOAK__CLIENT_SECRET=your-client-secret
```

### Step 6: Set Up PostgreSQL (If Using Database)

**On Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**On macOS:**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**On Windows:**
Download and install from [PostgreSQL Downloads](https://www.postgresql.org/download/windows/)

**Create Database:**
```bash
# Connect to PostgreSQL
sudo -u postgres psql  # Linux
psql postgres          # macOS/Windows

# Create database and user
CREATE DATABASE app_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE app_db TO postgres;
\q
```

### Step 7: Run Database Migrations (If Using Database)

```bash
# Create initial migration (if needed)
python manage.py makemigrations -m "initial migration"

# Apply migrations
python manage.py migrate
```

### Step 8: Verify Installation

Check that all dependencies are installed:
```bash
python -c "import fastapi, sqlalchemy, uvicorn; print('All dependencies installed!')"
```

---

## Installation With Docker

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd microservices-fastapi-template
```

### Step 2: Install Docker and Docker Compose

**On Linux (Ubuntu/Debian):**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Add user to docker group (optional, to run without sudo)
sudo usermod -aG docker $USER
newgrp docker
```

**On macOS:**
```bash
# Install Docker Desktop (includes Docker Compose)
brew install --cask docker
```

**On Windows:**
Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/)

**Verify Installation:**
```bash
docker --version
docker compose version
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp envs/env.dev .env  # Or create manually
```

Edit `.env` and configure your settings. **Important**: In Docker, use service names for database host:

```bash
# Application Settings
APP_SECRET_KEY=your-secret-key-here-minimum-32-characters-long
APP_DEBUG=true
APP_LOG_LEVEL=INFO
APP_HOST=0.0.0.0
APP_PORT=8000

# Database Configuration (IMPORTANT: Use service name 'postgres' in Docker)
APP_DATABASE__ENABLED=true
APP_DATABASE__HOST=postgres  # Use service name, NOT localhost
APP_DATABASE__PORT=5432
APP_DATABASE__NAME=app_db
APP_DATABASE__USER=postgres
APP_DATABASE__PASSWORD=postgres

# Environment
ENV=development
```

**⚠️ Important Docker Note**:
- Use `postgres` as the database host (service name), not `localhost`
- The entrypoint script will auto-fix `localhost` to `postgres` if detected

### Step 4: Build Docker Images

```bash
# Build all services
docker compose build

# Or build specific service
docker compose build app
```

### Step 5: Start Services

```bash
# Start all services in detached mode
docker compose up -d

# Or start with logs visible
docker compose up
```

### Step 6: Verify Installation

Check that containers are running:
```bash
docker compose ps
```

You should see:
- `fastapi-postgres` (PostgreSQL database)
- `fastapi-app` (FastAPI application)

Check application logs:
```bash
docker compose logs app
```

### Step 7: Run Database Migrations (If Using Database)

Migrations run automatically on container startup via the entrypoint script. To run manually:

```bash
# Run migrations manually
docker compose exec app python manage.py migrate

# Check migration status
docker compose exec app python manage.py show-applied
```

---

## Post-Installation Verification

### Without Docker

1. **Start the application:**
   ```bash
   python manage.py runserver
   ```

2. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Check version:**
   ```bash
   curl http://localhost:8000/version
   ```

### With Docker

1. **Check container status:**
   ```bash
   docker compose ps
   ```

2. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **View logs:**
   ```bash
   docker compose logs -f app
   ```

---

## Troubleshooting

### Common Issues

#### Python Version Mismatch
**Problem**: `python --version` shows version < 3.12

**Solution**:
```bash
# Install Python 3.12
# Linux
sudo apt install python3.12 python3.12-venv

# macOS
brew install python@3.12

# Use specific version
python3.12 -m venv .venv
```

#### Database Connection Issues (Without Docker)
**Problem**: Cannot connect to PostgreSQL

**Solution**:
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check connection settings in `.env`
- Verify database exists: `psql -U postgres -l`
- Check firewall settings

#### Database Connection Issues (With Docker)
**Problem**: Cannot connect to database in Docker

**Solution**:
- **Use service name `postgres`, not `localhost`** in `.env`
- Verify containers are on same network: `docker compose ps`
- Check database container logs: `docker compose logs postgres`
- Verify health check: `docker compose exec postgres pg_isready -U postgres`

#### Port Already in Use
**Problem**: Port 8000 is already in use

**Solution**:
```bash
# Find process using port
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# Change port in .env
APP_PORT=8001
```

#### Permission Denied (Docker)
**Problem**: Permission denied when running Docker commands

**Solution**:
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Or use sudo (not recommended)
sudo docker compose up
```

#### Migration Errors
**Problem**: Migrations fail to run

**Solution**:
```bash
# Check database connection
python manage.py show-config | grep DATABASE

# Verify database exists
psql -U postgres -l  # Without Docker
docker compose exec postgres psql -U postgres -l  # With Docker

# Reset migrations (careful: deletes data)
python manage.py downgrade -r base
python manage.py migrate
```

---

## Next Steps

After successful installation:

1. **Read the [Up and Running Guide](./up-and-running.md)** to learn how to run the application
2. **Review the [README.md](../README.md)** for project overview
3. **Check [Configuration Guide](../README.md#configuration)** for detailed settings
4. **Explore the [API Documentation](../README.md#api-endpoints)** for available endpoints

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

## Support

If you encounter issues not covered in this guide:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review application logs: `docker compose logs app` (Docker) or check console output (without Docker)
3. Verify environment variables: `python manage.py show-config`
4. Check GitHub issues for similar problems
