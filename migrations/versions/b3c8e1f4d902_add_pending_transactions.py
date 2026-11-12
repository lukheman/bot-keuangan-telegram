"""add pending_transactions table

Revision ID: b3c8e1f4d902
Revises: f7b2c9d1a4e8
Create Date: 2026-11-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c8e1f4d902'
down_revision: Union[str, Sequence[str], None] = 'f7b2c9d1a4e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pending_transactions',
        sa.Column('token', sa.String(length=12), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name=op.f('fk_pending_transactions_user_id_users'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_pending_transactions')),
    )
    with op.batch_alter_table('pending_transactions', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_pending_transactions_expires_at'),
            ['expires_at'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_pending_transactions_token'),
            ['token'],
            unique=True,
        )
        batch_op.create_index(
            batch_op.f('ix_pending_transactions_user_id'),
            ['user_id'],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('pending_transactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pending_transactions_user_id'))
        batch_op.drop_index(batch_op.f('ix_pending_transactions_token'))
        batch_op.drop_index(batch_op.f('ix_pending_transactions_expires_at'))

    op.drop_table('pending_transactions')
