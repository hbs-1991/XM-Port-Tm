"""Fix origin_country constraint to allow 2-3 character codes

Revision ID: 35255bbda367
Revises: 002
Create Date: 2025-09-01 20:31:03.426690

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35255bbda367'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old constraint that required exactly 3 characters
    op.drop_constraint('valid_origin_country', 'product_matches', type_='check')
    
    # Add the new constraint that allows 2-3 characters
    op.create_check_constraint(
        'valid_origin_country', 
        'product_matches', 
        'length(origin_country) >= 2 AND length(origin_country) <= 3'
    )


def downgrade() -> None:
    # Drop the new constraint
    op.drop_constraint('valid_origin_country', 'product_matches', type_='check')
    
    # Restore the old constraint (exactly 3 characters)
    op.create_check_constraint(
        'valid_origin_country', 
        'product_matches', 
        'length(origin_country) = 3'
    )