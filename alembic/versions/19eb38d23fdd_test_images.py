"""test_images

Revision ID: 19eb38d23fdd
Revises: 7a65c081de42
Create Date: 2025-09-22 02:29:41.332694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19eb38d23fdd'
down_revision: Union[str, Sequence[str], None] = '7a65c081de42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
