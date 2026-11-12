"""seed report templates

Revision ID: 72873af2112e
Revises: 80f7d3669540
Create Date: 2026-11-12 14:37:28.169826

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.modules.report_content.seed_data import GUIDANCE, PARAGRAPHS


# revision identifiers, used by Alembic.
revision: str = '72873af2112e'
down_revision: Union[str, Sequence[str], None] = '80f7d3669540'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    for (index, color), body in PARAGRAPHS.items():
        conn.execute(
            sa.text("INSERT INTO index_paragraph_templates (index_name, color, body) VALUES (:i, :c, :b)"),
            {"i": index, "c": color, "b": body},
        )
    for index, g in GUIDANCE.items():
        conn.execute(
            sa.text("INSERT INTO index_guidance_templates (index_name, special_instructions, practical_actions) "
                    "VALUES (:i, :s, :a)"),
            {"i": index, "s": g["special_instructions"], "a": g["practical_actions"]},
        )


def downgrade() -> None:
    op.execute("DELETE FROM index_guidance_templates")
    op.execute("DELETE FROM index_paragraph_templates")
