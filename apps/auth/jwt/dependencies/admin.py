"""Authorization dependency for the JWT-mode admin API."""

from apps.auth.rbac import require_permissions
from config.settings import settings

# Guard for every group/role/permission/user admin endpoint.
require_admin = require_permissions(str(settings.auth.JWT_ADMIN_PERMISSION))
