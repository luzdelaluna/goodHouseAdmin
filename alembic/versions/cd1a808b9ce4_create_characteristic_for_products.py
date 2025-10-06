"""Create characteristic for products

Revision ID: cd1a808b9ce4
Revises: 6b8b8b6d70ca
Create Date: 2025-10-06 06:12:37.939459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd1a808b9ce4'
down_revision: Union[str, Sequence[str], None] = '6b8b8b6d70ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
