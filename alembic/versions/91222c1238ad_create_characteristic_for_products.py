"""Create characteristic for products

Revision ID: 91222c1238ad
Revises: 9b00be21e6b1
Create Date: 2025-10-06 06:16:29.679994

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91222c1238ad'
down_revision: Union[str, Sequence[str], None] = '9b00be21e6b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
