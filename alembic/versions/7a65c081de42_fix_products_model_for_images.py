"""fix_products_model_for_images

Revision ID: 7a65c081de42
Revises: 67d8e7eedf0b
Create Date: 2025-09-21 22:04:53.244574

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a65c081de42'
down_revision: Union[str, Sequence[str], None] = '67d8e7eedf0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
