"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create enums
    op.execute("CREATE TYPE userrole AS ENUM ('super_admin', 'admin', 'manager', 'team_lead', 'employee')")
    op.execute("CREATE TYPE managerdomain AS ENUM ('parking', 'desk', 'cafeteria', 'attendance', 'it_support', 'floor_planning', 'general')")
    op.execute("CREATE TYPE celltype AS ENUM ('desk', 'parking_slot', 'cafeteria_table', 'path', 'wall', 'window', 'entry', 'exit', 'empty')")
    op.execute("CREATE TYPE celldirection AS ENUM ('up', 'down', 'left', 'right', 'multi')")
    op.execute("CREATE TYPE parkingtype AS ENUM ('employee', 'visitor')")
    op.execute("CREATE TYPE bookingstatus AS ENUM ('pending', 'confirmed', 'cancelled', 'completed')")
    op.execute("CREATE TYPE orderstatus AS ENUM ('pending', 'preparing', 'ready', 'delivered', 'cancelled')")
    op.execute("CREATE TYPE attendancestatus AS ENUM ('draft', 'pending_manager', 'approved', 'rejected')")
    op.execute("CREATE TYPE leavetype AS ENUM ('sick', 'casual', 'annual', 'unpaid')")
    op.execute("CREATE TYPE leavestatus AS ENUM ('pending', 'approved_level1', 'approved', 'rejected', 'cancelled')")
    op.execute("CREATE TYPE assetstatus AS ENUM ('available', 'assigned', 'maintenance', 'retired')")
    op.execute("CREATE TYPE assettype AS ENUM ('laptop', 'desktop', 'monitor', 'keyboard', 'mouse', 'headset', 'server', 'network_equipment', 'mobile_device', 'other')")
    op.execute("CREATE TYPE itrequesttype AS ENUM ('repair', 'replacement', 'new')")
    op.execute("CREATE TYPE itrequeststatus AS ENUM ('pending', 'approved', 'in_progress', 'completed', 'rejected')")
    op.execute("CREATE TYPE projectstatus AS ENUM ('draft', 'pending', 'approved', 'rejected', 'in_progress', 'completed', 'cancelled')")
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('employee_id', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('role', sa.Enum('super_admin', 'admin', 'manager', 'team_lead', 'employee', name='userrole', create_type=False), nullable=False, default='employee'),
        sa.Column('manager_domain', sa.Enum('parking', 'desk', 'cafeteria', 'attendance', 'it_support', 'floor_planning', 'general', name='managerdomain', create_type=False), nullable=True),
        sa.Column('is_team_lead', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('team_lead_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('manager_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create buildings table
    op.create_table(
        'buildings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('total_floors', sa.Integer(), default=1),
        sa.Column('has_basement', sa.Boolean(), default=False),
        sa.Column('basement_floors', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create floor_plans table
    op.create_table(
        'floor_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('floor_number', sa.Integer(), nullable=False),
        sa.Column('rows', sa.Integer(), nullable=False),
        sa.Column('columns', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_basement', sa.Boolean(), default=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('current_version', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('building_id', 'floor_number', name='uq_floor_plans_building_floor'),
    )
    
    # Create floor_plan_versions table
    op.create_table(
        'floor_plan_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('floor_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floor_plans.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('grid_data', postgresql.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('change_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('floor_plan_id', 'version', name='uq_floor_plan_versions'),
    )
    
    # Create parking_allocations table
    op.create_table(
        'parking_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('floor_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floor_plans.id'), nullable=False),
        sa.Column('slot_label', sa.String(50), nullable=False),
        sa.Column('cell_row', sa.String(10), nullable=False),
        sa.Column('cell_column', sa.String(10), nullable=False),
        sa.Column('parking_type', sa.Enum('employee', 'visitor', name='parkingtype', create_type=False), nullable=False, default='employee'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('visitor_name', sa.String(200), nullable=True),
        sa.Column('visitor_phone', sa.String(20), nullable=True),
        sa.Column('visitor_company', sa.String(200), nullable=True),
        sa.Column('vehicle_number', sa.String(50), nullable=True),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create parking_history table
    op.create_table(
        'parking_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('allocation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('parking_allocations.id'), nullable=False),
        sa.Column('floor_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floor_plans.id'), nullable=False),
        sa.Column('slot_label', sa.String(50), nullable=False),
        sa.Column('parking_type', sa.Enum('employee', 'visitor', name='parkingtype', create_type=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('visitor_name', sa.String(200), nullable=True),
        sa.Column('vehicle_number', sa.String(50), nullable=True),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create desk_bookings table
    op.create_table(
        'desk_bookings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('floor_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floor_plans.id'), nullable=False),
        sa.Column('floor_plan_version', sa.String(10), nullable=False),
        sa.Column('desk_label', sa.String(50), nullable=False),
        sa.Column('cell_row', sa.String(10), nullable=False),
        sa.Column('cell_column', sa.String(10), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('booking_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'cancelled', 'completed', name='bookingstatus', create_type=False), default='confirmed'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_desk_booking_date', 'desk_bookings', ['floor_plan_id', 'desk_label', 'booking_date'])
    
    # Create cafeteria_table_bookings table
    op.create_table(
        'cafeteria_table_bookings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('floor_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floor_plans.id'), nullable=False),
        sa.Column('table_label', sa.String(50), nullable=False),
        sa.Column('cell_row', sa.String(10), nullable=False),
        sa.Column('cell_column', sa.String(10), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('booking_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('guest_count', sa.String(10), default='1'),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'cancelled', 'completed', name='bookingstatus', create_type=False), default='confirmed'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create food_items table
    op.create_table(
        'food_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('ingredients', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('calories', sa.Integer(), nullable=True),
        sa.Column('is_available', sa.Boolean(), default=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('preparation_time_minutes', sa.Integer(), default=15),
        sa.Column('embedding', sa.Column('embedding', sa.LargeBinary(), nullable=True)),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Add vector column for food_items (pgvector)
    op.execute('ALTER TABLE food_items ADD COLUMN embedding vector(384)')
    
    # Create food_orders table
    op.create_table(
        'food_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_number', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'preparing', 'ready', 'delivered', 'cancelled', name='orderstatus', create_type=False), default='pending'),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=True),
        sa.Column('scheduled_time', sa.Time(), nullable=True),
        sa.Column('is_scheduled', sa.Boolean(), default=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create food_order_items table
    op.create_table(
        'food_order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('food_orders.id'), nullable=False),
        sa.Column('food_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('food_items.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('total_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('special_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create attendances table
    op.create_table(
        'attendances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum('draft', 'pending_manager', 'approved', 'rejected', name='attendancestatus', create_type=False), default='draft'),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'date', name='uq_attendance_user_date'),
    )
    
    # Create attendance_entries table
    op.create_table(
        'attendance_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('attendance_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('attendances.id'), nullable=False),
        sa.Column('check_in', sa.DateTime(timezone=True), nullable=False),
        sa.Column('check_out', sa.DateTime(timezone=True), nullable=True),
        sa.Column('entry_type', sa.String(50), default='regular'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create leave_types table
    op.create_table(
        'leave_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.Enum('sick', 'casual', 'annual', 'unpaid', name='leavetype', create_type=False), unique=True, nullable=False),
        sa.Column('default_days', sa.Integer(), default=0),
        sa.Column('is_paid', sa.Boolean(), default=True),
        sa.Column('requires_approval', sa.Boolean(), default=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create leave_balances table
    op.create_table(
        'leave_balances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('leave_type_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('leave_types.id'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('total_days', sa.Numeric(5, 1), nullable=False),
        sa.Column('used_days', sa.Numeric(5, 1), default=0),
        sa.Column('pending_days', sa.Numeric(5, 1), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'leave_type_id', 'year', name='uq_leave_balance'),
    )
    
    # Create leave_requests table
    op.create_table(
        'leave_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('leave_type_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('leave_types.id'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('total_days', sa.Numeric(5, 1), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'approved_level1', 'approved', 'rejected', 'cancelled', name='leavestatus', create_type=False), default='pending'),
        sa.Column('level1_approved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('level1_approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('level1_notes', sa.Text(), nullable=True),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create it_assets table
    op.create_table(
        'it_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('asset_id', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('asset_type', sa.Enum('laptop', 'desktop', 'monitor', 'keyboard', 'mouse', 'headset', 'server', 'network_equipment', 'mobile_device', 'other', name='assettype', create_type=False), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('vendor', sa.String(200), nullable=True),
        sa.Column('model', sa.String(200), nullable=True),
        sa.Column('serial_number', sa.String(200), unique=True, nullable=True),
        sa.Column('specifications', postgresql.JSONB(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('purchase_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('warranty_expiry', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('available', 'assigned', 'maintenance', 'retired', name='assetstatus', create_type=False), default='available'),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Add vector column for it_assets (pgvector)
    op.execute('ALTER TABLE it_assets ADD COLUMN embedding vector(384)')
    
    # Create it_asset_assignments table
    op.create_table(
        'it_asset_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('it_assets.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('assigned_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create it_requests table
    op.create_table(
        'it_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('request_number', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('request_type', sa.Enum('repair', 'replacement', 'new', name='itrequesttype', create_type=False), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('it_assets.id'), nullable=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(20), default='medium'),
        sa.Column('status', sa.Enum('pending', 'approved', 'in_progress', 'completed', 'rejected', name='itrequeststatus', create_type=False), default='pending'),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('assigned_to_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completion_notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requested_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('justification', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'pending', 'approved', 'rejected', 'in_progress', 'completed', 'cancelled', name='projectstatus', create_type=False), default='draft'),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create project_members table
    op.create_table(
        'project_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.String(100), default='member'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_project_member'),
    )
    
    # Insert default leave types
    op.execute("""
        INSERT INTO leave_types (id, name, code, default_days, is_paid, requires_approval, description) VALUES
        (gen_random_uuid(), 'Sick Leave', 'sick', 12, true, true, 'Leave for illness or medical appointments'),
        (gen_random_uuid(), 'Casual Leave', 'casual', 12, true, true, 'Leave for personal matters'),
        (gen_random_uuid(), 'Annual Leave', 'annual', 20, true, true, 'Annual vacation leave'),
        (gen_random_uuid(), 'Unpaid Leave', 'unpaid', 0, false, true, 'Leave without pay')
    """)
    
    # Insert default super admin user
    op.execute("""
        INSERT INTO users (id, employee_id, email, hashed_password, first_name, last_name, role, is_active)
        VALUES (
            gen_random_uuid(),
            'ADMIN-001',
            'super.admin@company.com',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.5a/5TA.Jk3Zvqa',
            'Super',
            'Admin',
            'super_admin',
            true
        )
    """)


def downgrade() -> None:
    # Drop all tables
    op.drop_table('project_members')
    op.drop_table('projects')
    op.drop_table('it_requests')
    op.drop_table('it_asset_assignments')
    op.drop_table('it_assets')
    op.drop_table('leave_requests')
    op.drop_table('leave_balances')
    op.drop_table('leave_types')
    op.drop_table('attendance_entries')
    op.drop_table('attendances')
    op.drop_table('food_order_items')
    op.drop_table('food_orders')
    op.drop_table('food_items')
    op.drop_table('cafeteria_table_bookings')
    op.drop_table('desk_bookings')
    op.drop_table('parking_history')
    op.drop_table('parking_allocations')
    op.drop_table('floor_plan_versions')
    op.drop_table('floor_plans')
    op.drop_table('buildings')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS projectstatus')
    op.execute('DROP TYPE IF EXISTS itrequeststatus')
    op.execute('DROP TYPE IF EXISTS itrequesttype')
    op.execute('DROP TYPE IF EXISTS assettype')
    op.execute('DROP TYPE IF EXISTS assetstatus')
    op.execute('DROP TYPE IF EXISTS leavestatus')
    op.execute('DROP TYPE IF EXISTS leavetype')
    op.execute('DROP TYPE IF EXISTS attendancestatus')
    op.execute('DROP TYPE IF EXISTS orderstatus')
    op.execute('DROP TYPE IF EXISTS bookingstatus')
    op.execute('DROP TYPE IF EXISTS parkingtype')
    op.execute('DROP TYPE IF EXISTS celldirection')
    op.execute('DROP TYPE IF EXISTS celltype')
    op.execute('DROP TYPE IF EXISTS managerdomain')
    op.execute('DROP TYPE IF EXISTS userrole')