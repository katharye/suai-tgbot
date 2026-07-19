"""Rename tg_users table and tg_id/tg_user_id columns to vk_users/vk_id/vk_user_id

Revision ID: b93c3bc80555
Revises: b8aefa4d137d
Create Date: 2026-07-19 17:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b93c3bc80555'
down_revision: Union[str, Sequence[str], None] = 'b8aefa4d137d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table('tg_users', 'vk_users')
    op.alter_column('vk_users', 'tg_id', new_column_name='vk_id')
    op.alter_column('homeworks', 'tg_user_id', new_column_name='vk_user_id')
    op.alter_column('filters', 'tg_user_id', new_column_name='vk_user_id')
    op.alter_column('hidden_subjects', 'tg_user_id', new_column_name='vk_user_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('hidden_subjects', 'vk_user_id', new_column_name='tg_user_id')
    op.alter_column('filters', 'vk_user_id', new_column_name='tg_user_id')
    op.alter_column('homeworks', 'vk_user_id', new_column_name='tg_user_id')
    op.alter_column('vk_users', 'vk_id', new_column_name='tg_id')
    op.rename_table('vk_users', 'tg_users')
