"""init_db

Revision ID: a7fdf6e88aef
Revises: 
Create Date: 2023-03-12 13:13:47.045248

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7fdf6e88aef"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "daily_hotwords_schedule",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bot_id", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("guild_id", sa.String(length=64), nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("time", sa.Time(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_id", "platform", "group_id", "guild_id", "channel_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("daily_hotwords_schedule")
    # ### end Alembic commands ###