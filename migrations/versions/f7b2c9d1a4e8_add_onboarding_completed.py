"""add onboarding_completed to users

Revision ID: f7b2c9d1a4e8
Revises: d2e4a61c9f08
Create Date: 2026-11-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b2c9d1a4e8'
down_revision: Union[str, Sequence[str], None] = 'd2e4a61c9f08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'onboarding_completed',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    # User lama tidak perlu mengulang onboarding.
    op.execute("UPDATE users SET onboarding_completed = true")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('onboarding_completed')
