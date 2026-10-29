"""cnic check constraint

Revision ID: 08382c3d8adb
Revises: 037ce41c90db
Create Date: 2026-10-29 11:46:37.690576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08382c3d8adb'
down_revision: Union[str, Sequence[str], None] = '037ce41c90db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint("cnic_13_digits", "users", "cnic ~ '^[0-9]{13}$'")


def downgrade() -> None:
    op.drop_constraint("ck_users_cnic_13_digits", "users", type_="check")
