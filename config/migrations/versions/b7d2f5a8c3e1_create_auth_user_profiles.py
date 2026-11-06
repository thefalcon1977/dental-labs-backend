"""create auth_user_profiles for local JWT users

Revision ID: b7d2f5a8c3e1
Revises: a1c4e7b2d9f0
Create Date: 2026-11-06 00:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: Union[str, None] = "b7d2f5a8c3e1"
down_revision: Union[str, None] = "a1c4e7b2d9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_user_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("bio", sa.String(length=500), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("locale", sa.String(length=16), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auth_user_profiles_user_id",
        "auth_user_profiles",
        ["user_id"],
        unique=True,
    )
    # Give existing local users an empty profile.
    op.execute(
        """
        INSERT INTO auth_user_profiles (id, user_id)
        SELECT gen_random_uuid()::text, id FROM auth_users
        """
    )


def downgrade() -> None:
    op.drop_index("ix_auth_user_profiles_user_id", table_name="auth_user_profiles")
    op.drop_table("auth_user_profiles")
