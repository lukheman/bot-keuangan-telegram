"""add ux_events table

Revision ID: c9d4f2a7b610
Revises: b3c8e1f4d902
Create Date: 2026-11-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d4f2a7b610'
down_revision: Union[str, Sequence[str], None] = 'b3c8e1f4d902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ux_events',
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('event', sa.String(length=50), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ux_events')),
    )
    with op.batch_alter_table('ux_events', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_ux_events_event'), ['event'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_ux_events_telegram_id'), ['telegram_id'], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('ux_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ux_events_telegram_id'))
        batch_op.drop_index(batch_op.f('ix_ux_events_event'))

    op.drop_table('ux_events')
