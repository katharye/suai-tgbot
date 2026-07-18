"""add_class_times_table

Revision ID: bba5cb937cc5
Revises: 84cf07fbc8fd
Create Date: 2026-07-16 17:15:53.140555

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bba5cb937cc5'
down_revision: Union[str, Sequence[str], None] = '84cf07fbc8fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'class_times',
        sa.Column('class_num', sa.Integer(), primary_key=True),
        sa.Column('start_time', sa.Integer(), nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('class_times')
