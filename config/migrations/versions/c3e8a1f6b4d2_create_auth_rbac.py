"""create groups, roles, permissions for local JWT users

Replaces the ``auth_users.roles`` JSON column with Keycloak-style RBAC:
users <-> groups, roles -> users/groups, permissions -> roles.
Existing JSON roles are migrated to ``auth_roles`` + ``auth_user_roles``.

Revision ID: c3e8a1f6b4d2
Revises: b7d2f5a8c3e1
Create Date: 2026-11-06 00:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: Union[str, None] = "c3e8a1f6b4d2"
down_revision: Union[str, None] = "b7d2f5a8c3e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match the auth.JWT_ADMIN_PERMISSION / auth.JWT_ADMIN_ROLE defaults.
ADMIN_PERMISSION = "auth:manage"
ADMIN_ROLE = "admin"
DEFAULT_ROLE = "user"

LINK_TABLES = (
    ("auth_user_groups", "user_id", "auth_users", "group_id", "auth_groups"),
    ("auth_user_roles", "user_id", "auth_users", "role_id", "auth_roles"),
    ("auth_group_roles", "group_id", "auth_groups", "role_id", "auth_roles"),
    (
        "auth_role_permissions",
        "role_id",
        "auth_roles",
        "permission_id",
        "auth_permissions",
    ),
)


def _create_named_table(name: str, column: str, length: int) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(column, sa.String(length=length), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(f"ix_{name}_{column}", name, [column], unique=True)


def upgrade() -> None:
    _create_named_table("auth_permissions", "code", 150)
    _create_named_table("auth_roles", "name", 100)
    _create_named_table("auth_groups", "name", 150)

    for name, left, left_table, right, right_table in LINK_TABLES:
        op.create_table(
            name,
            sa.Column(left, sa.String(length=36), nullable=False),
            sa.Column(right, sa.String(length=36), nullable=False),
            sa.ForeignKeyConstraint([left], [f"{left_table}.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint([right], [f"{right_table}.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint(left, right),
        )
        op.create_index(f"ix_{name}_{right}", name, [right])

    op.execute(
        sa.text(
            "INSERT INTO auth_permissions (id, code, description) "
            "VALUES (gen_random_uuid()::text, :code, "
            "'Manage groups, roles, permissions and user access')"
        ).bindparams(code=ADMIN_PERMISSION)
    )
    op.execute(
        sa.text(
            "INSERT INTO auth_roles (id, name, description) VALUES "
            "(gen_random_uuid()::text, :admin, 'Administrator'), "
            "(gen_random_uuid()::text, :user, 'Default role for registered users')"
        ).bindparams(admin=ADMIN_ROLE, user=DEFAULT_ROLE)
    )
    op.execute(
        sa.text(
            "INSERT INTO auth_role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM auth_roles r, auth_permissions p "
            "WHERE r.name = :admin AND p.code = :code"
        ).bindparams(admin=ADMIN_ROLE, code=ADMIN_PERMISSION)
    )

    # Carry over roles from the legacy JSON column.
    op.execute(
        "INSERT INTO auth_roles (id, name) "
        "SELECT gen_random_uuid()::text, legacy.name FROM ("
        "  SELECT DISTINCT json_array_elements_text(roles::json) AS name"
        "  FROM auth_users"
        ") legacy "
        "WHERE legacy.name <> '' AND length(legacy.name) <= 100 "
        "ON CONFLICT (name) DO NOTHING"
    )
    op.execute(
        "INSERT INTO auth_user_roles (user_id, role_id) "
        "SELECT DISTINCT u.id, r.id FROM auth_users u "
        "CROSS JOIN LATERAL json_array_elements_text(u.roles::json) AS legacy(name) "
        "JOIN auth_roles r ON r.name = legacy.name "
        "ON CONFLICT DO NOTHING"
    )
    op.drop_column("auth_users", "roles")


def downgrade() -> None:
    op.add_column(
        "auth_users",
        sa.Column(
            "roles", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")
        ),
    )
    # Only direct roles survive; group-inherited roles and permissions are lost.
    op.execute(
        "UPDATE auth_users u SET roles = sub.roles FROM ("
        "  SELECT ur.user_id, json_agg(r.name ORDER BY r.name) AS roles"
        "  FROM auth_user_roles ur JOIN auth_roles r ON r.id = ur.role_id"
        "  GROUP BY ur.user_id"
        ") sub WHERE sub.user_id = u.id"
    )
    op.alter_column("auth_users", "roles", server_default=None)

    for name, _left, _lt, right, _rt in reversed(LINK_TABLES):
        op.drop_index(f"ix_{name}_{right}", table_name=name)
        op.drop_table(name)
    for name, column in (
        ("auth_groups", "name"),
        ("auth_roles", "name"),
        ("auth_permissions", "code"),
    ):
        op.drop_index(f"ix_{name}_{column}", table_name=name)
        op.drop_table(name)
