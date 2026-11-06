# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Local JWT authentication mode (`auth.MODE = "jwt"`): register, login, refresh, and
  me endpoints under `/auth`, backed by a new `auth_users` table. Run migrations
  before enabling. Keycloak SSO (`auth.MODE = "sso"`) stays the default.
- Local user profiles (`auth_user_profiles`, one per user) with
  `GET`/`PATCH /auth/me/profile` in JWT mode.
- Keycloak-style access control for JWT mode: users belong to groups, roles are
  granted to users and groups, and roles bundle permissions. Access tokens carry
  the user's effective roles, groups, and permissions.
- Admin API under `/auth` (`/permissions`, `/roles`, `/groups`, `/users`) to manage
  them, guarded by the `auth.JWT_ADMIN_PERMISSION` permission (default
  `auth:manage`). The built-in `admin` role cannot be deleted or renamed.
- `python manage.py create-admin` to create the first administrator.
- Comprehensive rule system in `.cursor/rules/` for development standards
- Type alias system for better type safety
- Architecture decision records (ADR) guidelines

### Changed
- JWT mode: the `auth_users.roles` JSON column is replaced by the new role tables.
  The migration moves existing values over; `LocalUserResponse` no longer has
  `roles`. Access changes apply from the user's next login or token refresh.
- JWT repository split into `repository/dal/` and `repository/bll/` packages
  (user, profile, rbac modules).
- Refactored `apps/common` to follow proper directory structure
- Refactored `apps/core` to separate concerns and use type aliases
- Updated all code to use type aliases instead of inline patterns

### Removed
- Removed the Camunda application package and related runtime migration.

### Documentation
- Added README.md standards to global rules
- Added changelog maintenance guidelines

---

## [0.2.0] - 2024-01-XX

### Added
- Multi-app architecture with automatic router discovery
- SQLAlchemy 2.0 with async sessions
- Structured logging with structlog/loguru
- Health check endpoints (`/health`, `/live`, `/ready`)
- Database migration CLI commands
- Configuration management with Dynaconf
- Exception handling hierarchy
- Middleware system (CORS, rate limiting, security headers, logging, timing)

### Changed
- Migrated to Python 3.12+
- Updated to SQLAlchemy 2.0 syntax
- Improved type hints throughout codebase

---

## [0.1.0] - 2024-01-XX

### Added
- Initial project setup
- FastAPI application structure
- Basic health endpoints
- Database configuration
- Logging configuration
