"""Fix ITRequestType enum values and add holidays table

Revision ID: a1b2c3d4e5f6
Revises: 5c1a6edf8a08
Create Date: 2026-02-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5c1a6edf8a08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values to itrequesttype (use lowercase values)
    # PostgreSQL requires special handling for adding values to enums
    op.execute("ALTER TYPE itrequesttype ADD VALUE IF NOT EXISTS 'new_asset'")
    op.execute("ALTER TYPE itrequesttype ADD VALUE IF NOT EXISTS 'repair'")
    op.execute("ALTER TYPE itrequesttype ADD VALUE IF NOT EXISTS 'replacement'")
    op.execute("ALTER TYPE itrequesttype ADD VALUE IF NOT EXISTS 'software_install'")
    op.execute("ALTER TYPE itrequesttype ADD VALUE IF NOT EXISTS 'access_request'")
    op.execute("ALTER TYPE itrequesttype ADD VALUE IF NOT EXISTS 'network_issue'")
    op.execute("ALTER TYPE itrequesttype ADD VALUE IF NOT EXISTS 'other'")
    
    # Add missing value to itrequeststatus enum
    op.execute("ALTER TYPE itrequeststatus ADD VALUE IF NOT EXISTS 'cancelled'")
    
    # Add lowercase values to itrequestpriority enum
    op.execute("ALTER TYPE itrequestpriority ADD VALUE IF NOT EXISTS 'low'")
    op.execute("ALTER TYPE itrequestpriority ADD VALUE IF NOT EXISTS 'medium'")
    op.execute("ALTER TYPE itrequestpriority ADD VALUE IF NOT EXISTS 'high'")
    op.execute("ALTER TYPE itrequestpriority ADD VALUE IF NOT EXISTS 'critical'")
    
    # Add project status values if missing
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'pending_approval'")
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'on_hold'")
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'rejected'")
    
    # Create holidays table
    op.create_table('holidays',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('holiday_type', sa.String(length=50), nullable=True, server_default='company'),
        sa.Column('is_optional', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_by_code', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_code'], ['users.user_code'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index('ix_holiday_date', 'holidays', ['date'], unique=False)
    op.create_index('ix_holiday_active', 'holidays', ['is_active', 'date'], unique=False)


def downgrade() -> None:
    # Drop holidays table
    op.drop_index('ix_holiday_active', table_name='holidays')
    op.drop_index('ix_holiday_date', table_name='holidays')
    op.drop_table('holidays')
    # PostgreSQL doesn't support removing enum values
    # We just leave the new values in place
