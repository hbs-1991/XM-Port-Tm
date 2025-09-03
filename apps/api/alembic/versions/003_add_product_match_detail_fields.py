"""Add detailed fields to product_matches

Revision ID: 003
Revises: 002
Create Date: 2025-09-03 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('product_matches', sa.Column('unit_price', sa.DECIMAL(precision=12, scale=2), nullable=True))
    op.add_column('product_matches', sa.Column('packages_count', sa.Integer(), nullable=True))
    op.add_column('product_matches', sa.Column('packages_part', sa.String(length=20), nullable=True))
    op.add_column('product_matches', sa.Column('packaging_kind_code', sa.String(length=10), nullable=True))
    op.add_column('product_matches', sa.Column('packaging_kind_name', sa.String(length=100), nullable=True))
    op.add_column('product_matches', sa.Column('gross_weight', sa.DECIMAL(precision=10, scale=3), nullable=True))
    op.add_column('product_matches', sa.Column('net_weight', sa.DECIMAL(precision=10, scale=3), nullable=True))
    op.add_column('product_matches', sa.Column('supplementary_quantity', sa.DECIMAL(precision=12, scale=3), nullable=True))
    op.add_column('product_matches', sa.Column('supplementary_uom_code', sa.String(length=10), nullable=True))
    op.add_column('product_matches', sa.Column('supplementary_uom_name', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('product_matches', 'supplementary_uom_name')
    op.drop_column('product_matches', 'supplementary_uom_code')
    op.drop_column('product_matches', 'supplementary_quantity')
    op.drop_column('product_matches', 'net_weight')
    op.drop_column('product_matches', 'gross_weight')
    op.drop_column('product_matches', 'packaging_kind_name')
    op.drop_column('product_matches', 'packaging_kind_code')
    op.drop_column('product_matches', 'packages_part')
    op.drop_column('product_matches', 'packages_count')
    op.drop_column('product_matches', 'unit_price')

