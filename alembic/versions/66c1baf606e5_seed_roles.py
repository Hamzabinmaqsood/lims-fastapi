"""seed roles

Revision ID: 66c1baf606e5
Revises: c2c88734c887
Create Date: 2026-10-28 14:37:39.212318

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66c1baf606e5'
down_revision: Union[str, Sequence[str], None] = 'c2c88734c887'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass


def upgrade() -> None:
    op.execute(
        "INSERT INTO roles (name) VALUES ('Farmer'), ('Response_Team'), ('SuperAdmin') "
        "ON CONFLICT (name) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM roles WHERE name IN ('Farmer', 'Response_Team', 'SuperAdmin')")
