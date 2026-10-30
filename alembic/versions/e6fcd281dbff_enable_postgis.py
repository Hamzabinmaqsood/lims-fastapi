"""enable postgis

Revision ID: e6fcd281dbff
Revises: 86a20e537dd6
Create Date: 2026-10-30 11:15:48.769270

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6fcd281dbff'
down_revision: Union[str, Sequence[str], None] = '86a20e537dd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS postgis")
