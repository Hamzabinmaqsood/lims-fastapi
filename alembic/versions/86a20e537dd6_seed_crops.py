"""seed crops

Revision ID: 86a20e537dd6
Revises: 15947ba6aeaf
Create Date: 2026-10-30 11:06:11.334868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86a20e537dd6'
down_revision: Union[str, Sequence[str], None] = '15947ba6aeaf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEASONS = {
    "Rabi": ["Wheat", "Mustard", "Gram"],
    "Kharif": ["Cotton", "Rice", "Maize", "Sugarcane"],
}


def upgrade() -> None:
    conn = op.get_bind()
    for season, crops in SEASONS.items():
        season_id = conn.execute(
            sa.text("INSERT INTO crop_seasons (name) VALUES (:n) RETURNING id"), {"n": season}
        ).scalar_one()
        for crop in crops:
            conn.execute(
                sa.text("INSERT INTO crop_types (season_id, name) VALUES (:s, :n)"),
                {"s": season_id, "n": crop},
            )


def downgrade() -> None:
    op.execute("DELETE FROM crop_types")
    op.execute("DELETE FROM crop_seasons")
