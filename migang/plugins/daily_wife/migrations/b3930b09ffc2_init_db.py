"""init_db

Revision ID: b3930b09ffc2
Revises:
Create Date: 2023-04-02 17:51:47.170977

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b3930b09ffc2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "daily_wife_dailywife",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("wife_id", sa.BigInteger(), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("daily_wife_dailywife")
    # ### end Alembic commands ###