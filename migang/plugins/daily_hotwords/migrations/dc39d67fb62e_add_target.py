"""add target

Revision ID: dc39d67fb62e
Revises:
Create Date: 2023-08-10 19:22:35.717613

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "dc39d67fb62e"
down_revision = "a7fdf6e88aef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("daily_hotwords_schedule", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "target",
                sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
                nullable=True,
            )
        )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("daily_hotwords_schedule", schema=None) as batch_op:
        batch_op.drop_column("target")
    # ### end Alembic commands ###
