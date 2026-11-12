"""add personalization fields to users

Revision ID: e4b7c1d9a260
Revises: c9d4f2a7b610
Create Date: 2026-11-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4b7c1d9a260'
down_revision: Union[str, Sequence[str], None] = 'c9d4f2a7b610'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('nickname', sa.String(length=50), nullable=True)
        )
        batch_op.add_column(
            sa.Column('savings_target', sa.Numeric(15, 2), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('savings_target')
        batch_op.drop_column('nickname')
