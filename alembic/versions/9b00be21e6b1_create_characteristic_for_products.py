"""Create characteristic for products

Revision ID: 9b00be21e6b1
Revises: cd1a808b9ce4
Create Date: 2025-10-06 06:14:53.823222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b00be21e6b1'
down_revision: Union[str, Sequence[str], None] = 'cd1a808b9ce4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
