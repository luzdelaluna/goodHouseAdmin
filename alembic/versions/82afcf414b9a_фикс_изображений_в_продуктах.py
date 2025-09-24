"""фикс изображений в продуктах

Revision ID: 82afcf414b9a
Revises: 19eb38d23fdd
Create Date: 2025-09-24 02:25:18.652897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82afcf414b9a'
down_revision: Union[str, Sequence[str], None] = '19eb38d23fdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
