# Keycloak Configuration Guide

This guide explains how to configure Keycloak to work with the authentication service in this microservices template.

## Overview

The authentication service uses Keycloak as an identity and access management (IAM) solution. Keycloak provides:

- **User authentication** - Login, logout, token management
- **JWT token issuance** - Access tokens and refresh tokens
- **Role-based access control (RBAC)** - Realm roles and client roles
- **Permission management** - Fine-grained permissions
- **Group management** - User groups for access control

## Prerequisites

Before configuring Keycloak, ensure you have:

- Keycloak server installed and running (version 20.0+ recommended)
- Access to Keycloak Admin Console
- Admin credentials for Keycloak
- Understanding of OAuth 2.0 and OpenID Connect concepts

## Step 1: Install and Start Keycloak

### Using Docker

```bash
docker run -d \
  --name keycloak \
  -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:latest \
  start-dev
```

### Using Docker Compose

Add to your `docker-compose.yml`:

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
```

### Access Keycloak Admin Console

1. Open your browser and navigate to: `http://localhost:8080`
2. Click **Administration Console**
3. Login with admin credentials (default: `admin`/`admin`)

## Step 2: Create a Realm

A realm manages a set of users, credentials, roles, and groups. For production, create a dedicated realm (not the default `master` realm).

### Create New Realm

1. In Keycloak Admin Console, hover over the realm dropdown (top-left)
2. Click **Create Realm**
3. Enter realm name (e.g., `microservices-realm`)
4. Click **Create**

### Configure Realm Settings

1. Go to **Realm Settings** → **General**
2. Set **Display name** (optional)
3. Go to **Realm Settings** → **Login**
4. Enable **User registration** (if needed)
5. Enable **Forgot password** (if needed)
6. Go to **Realm Settings** → **Tokens**
7. Configure token lifetimes:
   - **Access Token Lifespan**: 5 minutes (default)
   - **SSO Session Idle**: 30 minutes
   - **SSO Session Max**: 10 hours

## Step 3: Create a Client

A client represents the application that will authenticate users through Keycloak.

### Step 3.1: General Settings

1. Go to **Clients** → **Create client**
2. You'll see a multi-step form. In **Step 1: General settings**, fill in:
   - **Client type**: Select `OpenID Connect` from the dropdown
   - **Client ID**: Enter `microservices-api` (or your preferred name)
     - This is a required field (marked with red asterisk)
     - This will be used as the `CLIENT_ID` in your application settings
   - **Name**: Optional display name for the client
   - **Description**: Optional description
   - **Always display in UI**: Leave as `Off` (default)
3. Click **Next** to proceed to capability configuration

### Step 3.2: Capability Config

1. In **Step 2: Capability config**, configure the following:

   **Client Authentication:**
   - Toggle **Client authentication** to `On`
     - This makes the client "confidential" and enables client secret authentication
     - Required for server-side applications

   **Authorization:**
   - Toggle **Authorization** to `On` (optional)
     - Only enable if you plan to use fine-grained permissions
     - Can be enabled later if needed

   **Authentication Flow:**
   - Check **Standard flow** (should be checked by default)
     - Required for authorization code flow
   - Check **Direct access grants**
     - Required for username/password login (used by `/auth/login` endpoint)
   - Leave other flows unchecked:
     - Implicit flow (deprecated)
     - Standard Token Exchange
     - OAuth 2.0 Device Authorization Grant
     - OIDC CIBA Grant
     - Service account roles (enable only if using service accounts)

   **PKCE Method:**
   - Leave as default or select `S256` if using PKCE

   **Require DPoP bound tokens:**
   - Leave as `Off` (default)

2. Click **Next** to proceed to login settings

### Step 3.3: Login Settings

1. In **Step 3: Login settings**, configure the following:

   **Root URL:**
   - Enter: `http://localhost:8000`
     - This is your API base URL
     - For production, use your actual domain (e.g., `https://api.yourdomain.com`)

   **Home URL:**
   - Enter: `http://localhost:8000`
     - Usually the same as Root URL

   **Valid redirect URIs:**
   - Click **+ Add valid redirect URIs**
   - Enter: `http://localhost:8000/*`
     - Allows redirects to any path under your API
     - For production, use specific paths or your domain
   - You can add multiple URIs if needed

   **Valid post logout redirect URIs:**
   - Click **+ Add valid post logout redirect URIs**
   - Enter: `http://localhost:8000/*`
     - Where users should be redirected after logout
   - Optional, but recommended

   **Web origins:**
   - Click **+ Add web origins**
   - Enter: `http://localhost:8000`
     - Allows CORS requests from this origin
     - For production, use your actual domain
   - You can add multiple origins if needed

2. Click **Save** to create the client

### Step 3.4: Get Client Secret

After creating the client, you need to get the client secret:

1. Go to **Clients** → Select your client (e.g., `microservices-api`)
2. Click on the **Credentials** tab
3. Copy the **Client secret** value
   - You'll need this for your application configuration
   - **Important**: Keep this secret secure and never commit it to version control
4. If no secret is shown or you need to regenerate it:
   - Click **Regenerate Secret**
   - Copy the new secret immediately (it won't be shown again)

### Step 3.5: Verify Client Configuration

After creating the client, verify the settings:

1. Go to **Clients** → Select your client → **Settings** tab
2. Verify:
   - **Client authentication**: `On` (confidential client)
   - **Standard flow**: `Enabled`
   - **Direct access grants**: `Enabled`
   - **Valid redirect URIs**: Contains your API URLs
   - **Web origins**: Contains your API domain
3. Go to **Credentials** tab:
   - Verify **Client secret** is set
   - Note the **Client ID** (you'll need both)

## Step 4: Configure Client Roles (Optional)

Client roles are specific to a client and useful for application-specific permissions.

### Create Client Roles

1. Go to **Clients** → Select your client → **Roles**
2. Click **Create role**
3. Enter role name (e.g., `admin`, `user`, `viewer`)
4. Add description (optional)
5. Click **Save**
6. Repeat for all needed roles

### Assign Roles to Users

1. Go to **Users** → Select a user → **Role mapping**
2. Click **Assign role**
3. Filter by **Filter by clients**
4. Select your client
5. Select roles to assign
6. Click **Assign**

## Step 5: Configure Realm Roles (Optional)

Realm roles apply across all clients in the realm.

### Create Realm Roles

1. Go to **Realm roles** → **Create role**
2. Enter role name (e.g., `super-admin`, `developer`)
3. Add description (optional)
4. Click **Save**

### Assign Realm Roles to Users

1. Go to **Users** → Select a user → **Role mapping**
2. Click **Assign role**
3. Filter by **Filter by realm roles**
4. Select roles to assign
5. Click **Assign**

## Step 6: Configure Groups (Optional)

Groups allow you to organize users and assign roles/permissions to entire groups.

### Create Groups

1. Go to **Groups** → **Create group**
2. Enter group name (e.g., `developers`, `admins`, `users`)
3. Click **Save**

### Assign Roles to Groups

1. Go to **Groups** → Select a group → **Role mapping**
2. Click **Assign role**
3. Select roles (realm or client roles)
4. Click **Assign**

### Add Users to Groups

1. Go to **Users** → Select a user → **Groups**
2. Click **Join group**
3. Select groups
4. Click **Join**

## Step 7: Create Test Users

### Create User

1. Go to **Users** → **Create new user**
2. Fill in:
   - **Username**: `testuser` (or your preferred username)
   - **Email**: `testuser@example.com`
   - **First name**: `Test`
   - **Last name**: `User`
   - **Email verified**: `ON` (for testing)
3. Click **Create**

### Set User Password

1. Go to **Users** → Select user → **Credentials**
2. Click **Set password**
3. Enter password
4. **Temporary**: `OFF` (so user doesn't need to change password on first login)
5. Click **Save**

### Assign Roles to User

1. Go to **Users** → Select user → **Role mapping**
2. Assign realm roles or client roles as needed
3. Click **Assign**

## Step 8: Configure Application Settings

Configure your application to connect to Keycloak using environment variables.

### Required Settings

Add to your `config/settings/settings.toml` or set as environment variables:

```toml
[keycloak]
SERVER_URL = "http://localhost:8080"
REALM = "microservices-realm"
CLIENT_ID = "microservices-api"
CLIENT_SECRET = "your-client-secret-here"
```

### Environment Variables

Alternatively, set environment variables:

```bash
export APP_KEYCLOAK__SERVER_URL="http://localhost:8080"
export APP_KEYCLOAK__REALM="microservices-realm"
export APP_KEYCLOAK__CLIENT_ID="microservices-api"
export APP_KEYCLOAK__CLIENT_SECRET="your-client-secret-here"
```

### Optional Settings

```toml
[keycloak]
# Token introspection (for additional validation)
TOKEN_INTROSPECTION_ENABLED = false

# JWT validation algorithms
ALGORITHMS = ["RS256"]

# Audience validation
AUDIENCE = "microservices-api"  # Optional, defaults to CLIENT_ID

# HTTP client settings
HTTP_TIMEOUT = 10.0
HTTP_CONNECT_TIMEOUT = 5.0
HTTP_MAX_CONNECTIONS = 100
HTTP_MAX_KEEPALIVE_CONNECTIONS = 20
HTTP_KEEPALIVE_EXPIRY = 30.0
```

## Step 9: Verify Configuration

### Test Login Endpoint

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "your-password"
  }'
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 300
}
```

### Test Token Validation

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Expected response:
```json
{
  "id": "user-uuid",
  "username": "testuser",
  "email": "testuser@example.com",
  "roles": {
    "realm_roles": ["user"],
    "client_roles": {
      "microservices-api": ["admin"]
    }
  },
  "permissions": {
    "permissions": []
  },
  "groups": []
}
```

## Step 10: Production Configuration

For production environments, consider:

### Security Best Practices

1. **Use HTTPS**: Always use HTTPS for Keycloak server URL
2. **Strong Client Secret**: Use a strong, randomly generated client secret
3. **Separate Realm**: Create a dedicated realm for production (not `master`)
4. **Token Lifetimes**: Configure appropriate token lifetimes
5. **Session Management**: Configure session timeouts appropriately
6. **Password Policy**: Enable password policies in realm settings
7. **Two-Factor Authentication**: Enable 2FA for sensitive applications
8. **Audit Logging**: Enable audit logging in Keycloak

### Environment Variables

```bash
# Production Keycloak configuration
export APP_KEYCLOAK__SERVER_URL="https://keycloak.yourdomain.com"
export APP_KEYCLOAK__REALM="production-realm"
export APP_KEYCLOAK__CLIENT_ID="production-api-client"
export APP_KEYCLOAK__CLIENT_SECRET="strong-random-secret"
```

### High Availability

- Deploy Keycloak in a cluster for high availability
- Use a shared database (PostgreSQL) for Keycloak
- Configure load balancing for Keycloak instances
- Use Redis for session replication

## Troubleshooting

### Common Issues

#### 1. "Invalid client credentials"

**Problem**: Client secret is incorrect or client authentication is not enabled.

**Solution**:
- Verify client secret in Keycloak Admin Console
- Ensure client has "Client authentication" enabled
- Check that `CLIENT_SECRET` matches the value in Keycloak

#### 2. "Invalid token signature"

**Problem**: JWT token signature cannot be verified.

**Solution**:
- Verify `SERVER_URL` and `REALM` are correct
- Check that Keycloak is accessible from your application
- Ensure JWKS endpoint is accessible: `{SERVER_URL}/realms/{REALM}/protocol/openid-connect/certs`

#### 3. "Token expired"

**Problem**: Access token has expired.

**Solution**:
- Use refresh token to get a new access token
- Increase access token lifespan in Keycloak (if needed)
- Implement token refresh logic in your application

#### 4. "Insufficient roles"

**Problem**: User doesn't have required roles.

**Solution**:
- Assign roles to user in Keycloak
- Verify roles are assigned at correct level (realm or client)
- Check role names match exactly (case-sensitive)

#### 5. "Connection refused"

**Problem**: Cannot connect to Keycloak server.

**Solution**:
- Verify Keycloak is running
- Check `SERVER_URL` is correct
- Ensure network connectivity
- Check firewall rules

## Additional Resources

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OpenID Connect Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 Specification](https://oauth.net/2/)

## Configuration Summary

After completing all steps, your Keycloak configuration should include:

- ✅ Keycloak server running and accessible
- ✅ Realm created and configured
- ✅ Client created with client authentication enabled
- ✅ Client secret obtained and configured
- ✅ Test users created with passwords
- ✅ Roles assigned to users (if using RBAC)
- ✅ Application settings configured with correct values
- ✅ Login endpoint tested and working

Your authentication service is now ready to use Keycloak for user authentication and authorization!
