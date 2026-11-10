"""farm name not blank

Revision ID: ffeef9a92ca3
Revises: ed9a86736904
Create Date: 2026-11-10 12:25:08.783419

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffeef9a92ca3'
down_revision: Union[str, Sequence[str], None] = 'ed9a86736904'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE farms SET name = 'farm' WHERE trim(name) = ''")   # fix existing blank rows first
    op.create_check_constraint("name_not_blank", "farms", "length(trim(name)) > 0")


def downgrade() -> None:
    op.drop_constraint("ck_farms_name_not_blank", "farms", type_="check")
