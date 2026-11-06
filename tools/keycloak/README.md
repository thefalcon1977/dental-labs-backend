# Keycloak Development Realm Export

This directory contains a pre-configured Keycloak realm export for development and testing purposes.

## Overview

The `dev.json` file contains a simplified Keycloak realm configuration optimized for local development:

- **Realm Name**: `development`
- **Client ID**: `microservices-api`
- **Client Secret**: `dev-client-secret-change-in-production` (⚠️ **Change this in production!**)
- **URLs**: All configured for `localhost` (ports 8000 and 3000)

## Features

### Development-Friendly Settings

- ✅ **User Registration**: Enabled (no email verification required)
- ✅ **Password Reset**: Enabled
- ✅ **Login with Email**: Enabled
- ✅ **Edit Username**: Enabled
- ✅ **Remember Me**: Enabled
- ✅ **SSL Required**: Disabled (for localhost)
- ✅ **Brute Force Protection**: Disabled (for easier testing)
- ✅ **Duplicate Emails**: Allowed (for testing multiple accounts)

### Simplified Roles

The realm includes only essential roles for development:

**Realm Roles:**
- `user` - Basic authenticated user
- `admin` - Administrator with full access
- `developer` - Developer role for testing
- `tester` - QA/testing role
- `offline_access` - For refresh tokens
- `uma_authorization` - For fine-grained permissions

**Client Roles:**
- `view-profile` - View user profile
- `manage-account` - Manage own account

### Client Configuration

**Client ID**: `microservices-api`

**Enabled Features:**
- Standard Flow (Authorization Code)
- Direct Access Grants (Username/Password)
- Service Accounts
- Refresh Tokens

**Redirect URIs:**
- `http://localhost:8000/*`
- `http://localhost:3000/*`
- `http://127.0.0.1:8000/*`
- `http://127.0.0.1:3000/*`

**Web Origins:**
- All localhost origins allowed (including `+` wildcard)

## Import Instructions

### Method 1: Using Keycloak Admin Console

1. Start Keycloak (if not already running):
   ```bash
   docker run -d \
     --name keycloak \
     -p 8080:8080 \
     -e KEYCLOAK_ADMIN=admin \
     -e KEYCLOAK_ADMIN_PASSWORD=admin \
     quay.io/keycloak/keycloak:latest \
     start-dev
   ```

2. Open Keycloak Admin Console:
   - Navigate to: `http://localhost:8080`
   - Login with: `admin` / `admin`

3. Import Realm:
   - Click on the realm dropdown (top-left)
   - Click **Create Realm**
   - Click **Import** button
   - Select `dev.json` file
   - Click **Create**

### Method 2: Using Keycloak Admin CLI

```bash
# Start Keycloak
docker run -d \
  --name keycloak \
  -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:latest \
  start-dev

# Wait for Keycloak to start (about 30 seconds)
sleep 30

# Import realm
docker exec -i keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password admin

docker exec -i keycloak /opt/keycloak/bin/kcadm.sh create realms \
  -f /dev/stdin < tools/keycloak/dev.json
```

### Method 3: Using Docker Compose

If you have a `docker-compose.yml` with Keycloak:

```yaml
services:
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    ports:
      - "8080:8080"
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
    command: start-dev
    volumes:
      - ./tools/keycloak/dev.json:/opt/keycloak/data/import/dev.json:ro
    entrypoint: /opt/keycloak/bin/kc.sh start-dev --import-realm
```

## Application Configuration

After importing the realm, update your application configuration:

### Environment Variables

```bash
APP_KEYCLOAK__SERVER_URL=http://localhost:8080
APP_KEYCLOAK__REALM=development
APP_KEYCLOAK__CLIENT_ID=microservices-api
APP_KEYCLOAK__CLIENT_SECRET=dev-client-secret-change-in-production
```

### settings.toml

```toml
[keycloak]
SERVER_URL = "http://localhost:8080"
REALM = "development"
CLIENT_ID = "microservices-api"
CLIENT_SECRET = "dev-client-secret-change-in-production"
```

## Pre-configured Test Data

The realm export includes pre-configured test groups and users for immediate testing:

### Test Groups

- **`developers`** - Contains `developer` and `user` roles
- **`testers`** - Contains `tester` and `user` roles
- **`admins`** - Contains `admin` and `user` roles
- **`users`** - Contains `user` role only

### Test Users

All test users have the password format: `{username}123` (e.g., `testuser123`)

| Username | Email | Password | Roles | Groups |
|----------|-------|----------|-------|--------|
| `testuser` | testuser@example.com | `testpass123` | `user` | `users` |
| `admin` | admin@example.com | `admin123` | `admin`, `user` | `admins` |
| `developer` | developer@example.com | `dev123` | `developer`, `user` | `developers` |
| `tester` | tester@example.com | `test123` | `tester`, `user` | `testers` |
| `multirole` | multirole@example.com | `multi123` | `developer`, `tester`, `user` | `developers`, `testers` |

### Quick Test Login

After importing the realm, you can immediately test authentication:

```bash
# Test as regular user
curl -X POST http://localhost:8080/realms/development/protocol/openid-connect/token \
  -d "client_id=microservices-api" \
  -d "client_secret=dev-client-secret-change-in-production" \
  -d "username=testuser" \
  -d "password=testpass123" \
  -d "grant_type=password"

# Test as admin
curl -X POST http://localhost:8080/realms/development/protocol/openid-connect/token \
  -d "client_id=microservices-api" \
  -d "client_secret=dev-client-secret-change-in-production" \
  -d "username=admin" \
  -d "password=admin123" \
  -d "grant_type=password"

# Test as developer
curl -X POST http://localhost:8080/realms/development/protocol/openid-connect/token \
  -d "client_id=microservices-api" \
  -d "client_secret=dev-client-secret-change-in-production" \
  -d "username=developer" \
  -d "password=dev123" \
  -d "grant_type=password"
```

## Testing Use Cases

### Test Different Roles

The pre-configured users allow you to test different role scenarios:

- **Regular User** (`testuser`): Basic `user` role only
- **Developer** (`developer`): `developer` and `user` roles
- **Admin** (`admin`): `admin` and `user` roles
- **Tester** (`tester`): `tester` and `user` roles
- **Multi-Role** (`multirole`): Multiple roles (`developer`, `tester`, `user`)

### Create Additional Test Users

If you need additional test users:

1. Go to **Users** → **Create new user**
2. Fill in:
   - **Username**: Your desired username
   - **Email**: Your email address
   - **Email verified**: `ON` (for easier testing)
   - **Enabled**: `ON`
3. Go to **Credentials** tab → Set password
4. Go to **Role mapping** tab → Assign roles
5. Go to **Groups** tab → Add to groups if needed

### Test Authentication Flows

1. **Direct Access Grant** (Username/Password):
   ```bash
   curl -X POST http://localhost:8080/realms/development/protocol/openid-connect/token \
     -d "client_id=microservices-api" \
     -d "client_secret=dev-client-secret-change-in-production" \
     -d "username=testuser" \
     -d "password=password" \
     -d "grant_type=password"
   ```

2. **Authorization Code Flow**: Use the `/auth/login` endpoint in your application

3. **Service Account**: Use client credentials grant for service-to-service auth

## Customization

### Add More Roles

1. Go to **Realm roles** → **Create role**
2. Add role name and description
3. Assign to users as needed

### Modify Client Settings

1. Go to **Clients** → `microservices-api` → **Settings**
2. Modify:
   - **Access Token Lifespan**: Currently 3600 seconds (1 hour)
   - **Redirect URIs**: Add your frontend URLs
   - **Web Origins**: Add CORS origins

### Enable Email Verification

1. Go to **Realm Settings** → **Login**
2. Enable **Email verification**
3. Configure SMTP settings in **Realm Settings** → **Email**

## Security Notes

⚠️ **This configuration is for DEVELOPMENT ONLY!**

**Do NOT use in production:**

- Client secret is hardcoded and weak
- SSL is disabled
- Brute force protection is disabled
- Token lifespans are long (for easier testing)
- All localhost origins are allowed

**For production:**
- Generate a strong client secret
- Enable SSL/TLS
- Enable brute force protection
- Set appropriate token lifespans
- Restrict redirect URIs and web origins
- Enable email verification
- Review all security settings

## Troubleshooting

### Realm Import Fails

- Ensure Keycloak is fully started (wait 30-60 seconds)
- Check that the JSON file is valid: `python -c "import json; json.load(open('dev.json'))"`
- Try importing via Admin Console instead of CLI

### Client Secret Not Working

- The client secret in the export is: `dev-client-secret-change-in-production`
- After import, you can regenerate it in **Clients** → `microservices-api` → **Credentials**
- Update your application configuration with the new secret

### Users Can't Login

- Check that user is **Enabled**
- Check that **Email verified** is ON (if email verification is enabled)
- Verify password is set in **Credentials** tab
- Check that user has the `default-roles-development` role assigned

### CORS Issues

- Ensure your frontend URL is in **Web origins**
- Check that **Valid redirect URIs** includes your callback URLs
- Verify `APP_KEYCLOAK__SERVER_URL` matches your Keycloak URL

## Additional Resources

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Keycloak Configuration Guide](../docs/source/keycloak-configuration.md)
- [OAuth 2.0 / OpenID Connect](https://oauth.net/2/)
