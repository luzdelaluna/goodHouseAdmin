"""Create characteristic for products

Revision ID: 6b8b8b6d70ca
Revises: c008bf3c48ef
Create Date: 2025-10-06 02:45:19.934836

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b8b8b6d70ca'
down_revision: Union[str, Sequence[str], None] = 'c008bf3c48ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
