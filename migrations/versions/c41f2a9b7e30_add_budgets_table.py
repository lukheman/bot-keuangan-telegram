"""add budgets table

Revision ID: c41f2a9b7e30
Revises: 186df9dab340
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c41f2a9b7e30'
down_revision: Union[str, Sequence[str], None] = '186df9dab340'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('budgets',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('category_id', sa.Uuid(), nullable=False),
    sa.Column('amount_limit', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_budgets_category_id_categories')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_budgets_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_budgets')),
    sa.UniqueConstraint('user_id', 'category_id', name='uq_budgets_user_id_category_id')
    )
    with op.batch_alter_table('budgets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_budgets_category_id'), ['category_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_budgets_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('budgets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_budgets_user_id'))
        batch_op.drop_index(batch_op.f('ix_budgets_category_id'))

    op.drop_table('budgets')
