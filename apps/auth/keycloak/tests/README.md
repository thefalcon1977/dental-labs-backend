# Authentication Tests

These tests use **real Keycloak implementations** - no mocks are used. All tests interact with actual Keycloak services.

## Prerequisites

1. **Keycloak must be running** and accessible
2. **Test user credentials** must be configured in environment variables
3. **Keycloak configuration** must be properly set in your environment

## Environment Variables

The tests require the following environment variables to be set:

```bash
# Test user credentials
TEST_USERNAME=your-test-username
TEST_PASSWORD=your-test-password
```

### Setting Environment Variables

#### Linux/macOS:
```bash
export TEST_USERNAME=testuser
export TEST_PASSWORD=testpassword
```

#### Windows (PowerShell):
```powershell
$env:TEST_USERNAME="testuser"
$env:TEST_PASSWORD="testpassword"
```

#### Windows (CMD):
```cmd
set TEST_USERNAME=testuser
set TEST_PASSWORD=testpassword
```

#### Using .env file:
Add to your `.env` file:
```
TEST_USERNAME=testuser
TEST_PASSWORD=testpassword
```

## Running Tests

### Run all authentication tests:
```bash
pytest apps/auth/tests/
```

### Run specific test file:
```bash
pytest apps/auth/tests/test_dependencies/test_auth.py
```

### Run with verbose output:
```bash
pytest apps/auth/tests/ -v
```

## Test Structure

- **test_dependencies/**: Tests for authentication and RBAC dependencies
- **test_services/**: Tests for authentication and token services
- **test_utils/**: Tests for JWT validator, Keycloak client, and token cache
- **test_integration/**: Integration tests for complete authentication flows

## Test Behavior

- Tests will **skip** if `TEST_USERNAME` or `TEST_PASSWORD` are not set
- Tests will **skip** if authentication fails (e.g., Keycloak is not accessible)
- All tests use **real tokens** obtained from Keycloak
- Tokens are obtained once per test session and reused where possible

## Notes

- Some tests may invalidate tokens (e.g., logout tests), which may affect subsequent tests
- Tests that require specific roles/permissions will skip if the test user doesn't have them
- Make sure your test user has appropriate roles and permissions configured in Keycloak
