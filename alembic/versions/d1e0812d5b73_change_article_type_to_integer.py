"""Change article type to integer

Revision ID: d1e0812d5b73
Revises: 82afcf414b9a
Create Date: 2025-09-24 03:32:53.197625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e0812d5b73'
down_revision: Union[str, Sequence[str], None] = '82afcf414b9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Сначала проверьте, есть ли нечисловые значения в article
    # Если есть, нужно их обработать

    # Вариант 1: Преобразуем только числовые строки, остальные в NULL
    op.execute("UPDATE products SET article = NULL WHERE article !~ '^[0-9]+$'")

    # Вариант 2: Извлечем числа из строк (если есть форматы типа "PRD-123")
    # op.execute("UPDATE products SET article = regexp_replace(article, '[^0-9]', '', 'g')")
    # op.execute("UPDATE products SET article = NULL WHERE article = ''")

    # Теперь изменяем тип с явным преобразованием
    op.alter_column('products', 'article',
                    type_=sa.Integer(),
                    postgresql_using='article::integer')


def downgrade():
    # Для отката преобразуем обратно в строку
    op.alter_column('products', 'article',
                    type_=sa.String(),
                    postgresql_using='article::text')
