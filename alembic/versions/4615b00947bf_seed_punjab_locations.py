"""seed punjab locations

Revision ID: 4615b00947bf
Revises: 7a59c1fffeb9
Create Date: 2026-10-29 10:48:26.922736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4615b00947bf'
down_revision: Union[str, Sequence[str], None] = '7a59c1fffeb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# def upgrade() -> None:
#     """Upgrade schema."""
#     pass


# def downgrade() -> None:
#     """Downgrade schema."""
#     pass


DATA = [
    ("Lahore", (31.520370, 74.358749), "Lahore City", (31.549722, 74.343611), "Lahore", (31.520370, 74.358749)),
    ("Faisalabad", (31.450365, 73.134964), "Jaranwala", (31.333000, 73.418000), "Jaranwala", (31.333000, 73.418000)),
    ("Multan", (30.157458, 71.524915), "Shujabad", (29.877000, 71.295000), "Shujabad", (29.877000, 71.295000)),
]


def upgrade() -> None:
    conn = op.get_bind()
    province_id = conn.execute(sa.text(
        "INSERT INTO provinces (name, latitude, longitude) "
        "VALUES ('Punjab', 31.170406, 72.709716) RETURNING id"
    )).scalar_one()

    for district, d, tehsil, t, city, c in DATA:
        district_id = conn.execute(sa.text(
            "INSERT INTO districts (province_id, name, latitude, longitude) "
            "VALUES (:p, :n, :lat, :lng) RETURNING id"
        ), {"p": province_id, "n": district, "lat": d[0], "lng": d[1]}).scalar_one()

        tehsil_id = conn.execute(sa.text(
            "INSERT INTO tehsils (district_id, name, latitude, longitude) "
            "VALUES (:d, :n, :lat, :lng) RETURNING id"
        ), {"d": district_id, "n": tehsil, "lat": t[0], "lng": t[1]}).scalar_one()

        conn.execute(sa.text(
            "INSERT INTO localities (tehsil_id, name, kind, latitude, longitude) "
            "VALUES (:t, :n, 'city', :lat, :lng)"
        ), {"t": tehsil_id, "n": city, "lat": c[0], "lng": c[1]})


def downgrade() -> None:
    # Children first, because of the RESTRICT foreign keys.
    op.execute("DELETE FROM localities")
    op.execute("DELETE FROM tehsils")
    op.execute("DELETE FROM districts")
    op.execute("DELETE FROM provinces")
