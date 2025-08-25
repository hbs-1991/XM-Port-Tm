"""Complete schema migration - clean implementation

Revision ID: 002
Revises: 001
Create Date: 2025-08-25 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== CREATE ENUM TYPES FIRST =====
    # Create new enum types that don't exist yet
    op.execute("CREATE TYPE subscriptiontier AS ENUM ('FREE', 'BASIC', 'PREMIUM', 'ENTERPRISE')")
    
    # ===== BILLING TRANSACTIONS TABLE =====
    op.create_table('billing_transactions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.Enum('CREDIT_PURCHASE', 'SUBSCRIPTION', 'REFUND', name='billingtransactiontype'), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('credits_granted', sa.Integer(), server_default='0', nullable=False),
        sa.Column('payment_provider', sa.String(length=50), nullable=False),
        sa.Column('payment_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', name='billingtransactionstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('amount >= 0', name='positive_amount'),
        sa.CheckConstraint('credits_granted >= 0', name='positive_credits_granted'),
        sa.CheckConstraint('length(currency) = 3', name='valid_currency_code'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # ===== PRODUCT MATCHES TABLE =====
    op.create_table('product_matches',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('product_description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.DECIMAL(precision=10, scale=3), nullable=False),
        sa.Column('unit_of_measure', sa.String(length=50), nullable=False),
        sa.Column('value', sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column('origin_country', sa.String(length=3), nullable=False),
        sa.Column('matched_hs_code', sa.String(length=10), nullable=False),
        sa.Column('confidence_score', sa.DECIMAL(precision=3, scale=2), nullable=False),
        sa.Column('alternative_hs_codes', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('vector_store_reasoning', sa.Text(), nullable=True),
        sa.Column('requires_manual_review', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('user_confirmed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='valid_confidence_score'),
        sa.CheckConstraint('length(origin_country) = 3', name='valid_origin_country'),
        sa.CheckConstraint('quantity > 0', name='positive_quantity'),
        sa.CheckConstraint('value >= 0', name='positive_value'),
        sa.ForeignKeyConstraint(['job_id'], ['processing_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # ===== UPDATE HS_CODES TABLE =====
    # Add new columns to hs_codes
    op.add_column('hs_codes', sa.Column('chapter', sa.String(length=2), nullable=False))
    op.add_column('hs_codes', sa.Column('section', sa.String(length=2), nullable=False))
    op.add_column('hs_codes', sa.Column('embedding', postgresql.JSONB(), nullable=True))
    op.add_column('hs_codes', sa.Column('country', sa.String(length=3), nullable=False))
    op.add_column('hs_codes', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('hs_codes', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

    # Modify existing columns in hs_codes
    op.alter_column('hs_codes', 'code',
        existing_type=sa.VARCHAR(length=10),
        type_=sa.String(length=10),
        existing_nullable=False)

    # Remove old columns from hs_codes
    op.drop_index('ix_hs_codes_code', table_name='hs_codes')
    op.drop_column('hs_codes', 'embedding_vector')
    op.drop_column('hs_codes', 'category')
    op.drop_column('hs_codes', 'is_restricted')
    op.drop_column('hs_codes', 'tariff_rate')
    op.drop_column('hs_codes', 'units')

    # Add hs_codes constraints
    op.create_check_constraint('valid_country_code', 'hs_codes', 'length(country) = 3')
    op.create_check_constraint('valid_chapter_code', 'hs_codes', 'length(chapter) = 2')
    op.create_check_constraint('valid_section_code', 'hs_codes', 'length(section) = 2')

    # ===== UPDATE USERS TABLE =====
    # Add new columns to users
    op.add_column('users', sa.Column('subscription_tier', sa.Enum('FREE', 'BASIC', 'PREMIUM', 'ENTERPRISE', name='subscriptiontier'), server_default='FREE', nullable=False))
    op.add_column('users', sa.Column('credits_remaining', sa.Integer(), server_default='2', nullable=False))
    op.add_column('users', sa.Column('credits_used_this_month', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('first_name', sa.String(length=50), nullable=False))
    op.add_column('users', sa.Column('last_name', sa.String(length=50), nullable=False))
    op.add_column('users', sa.Column('company_name', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('country', sa.String(length=3), nullable=False))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))

    # Update users role enum to include PROJECT_OWNER (only if it doesn't exist)
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'PROJECT_OWNER'")

    # Modify existing users columns
    op.alter_column('users', 'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False)

    # Remove old columns from users
    op.drop_index('ix_users_id', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_column('users', 'name')
    op.drop_column('users', 'credits')

    # Add users constraints
    op.create_check_constraint('positive_credits', 'users', 'credits_remaining >= 0')
    op.create_check_constraint('positive_credits_used', 'users', 'credits_used_this_month >= 0')
    op.create_check_constraint('valid_country_code', 'users', 'length(country) = 3')
    op.create_unique_constraint('uq_users_email', 'users', ['email'])

    # ===== UPDATE PROCESSING_JOBS TABLE =====
    # Add new columns to processing_jobs
    op.add_column('processing_jobs', sa.Column('input_file_name', sa.String(length=255), nullable=False))
    op.add_column('processing_jobs', sa.Column('input_file_url', sa.Text(), nullable=False))
    op.add_column('processing_jobs', sa.Column('input_file_size', sa.BIGINT(), nullable=False))
    op.add_column('processing_jobs', sa.Column('output_xml_url', sa.Text(), nullable=True))
    op.add_column('processing_jobs', sa.Column('xml_generation_status', sa.String(length=20), nullable=True))
    op.add_column('processing_jobs', sa.Column('xml_generated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('processing_jobs', sa.Column('xml_file_size', sa.Integer(), nullable=True))
    op.add_column('processing_jobs', sa.Column('credits_used', sa.Integer(), server_default='0', nullable=False))
    op.add_column('processing_jobs', sa.Column('processing_time_ms', sa.Integer(), nullable=True))
    op.add_column('processing_jobs', sa.Column('total_products', sa.Integer(), server_default='0', nullable=False))
    op.add_column('processing_jobs', sa.Column('successful_matches', sa.Integer(), server_default='0', nullable=False))
    op.add_column('processing_jobs', sa.Column('average_confidence', sa.DECIMAL(precision=3, scale=2), nullable=True))
    op.add_column('processing_jobs', sa.Column('country_schema', sa.String(length=3), nullable=False))
    op.add_column('processing_jobs', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))

    # Update processing_jobs status enum to include new statuses
    op.execute("ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'COMPLETED_WITH_ERRORS'")
    op.execute("ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'CANCELLED'")

    # Modify existing processing_jobs columns
    op.alter_column('processing_jobs', 'error_message',
        existing_type=sa.VARCHAR(),
        type_=sa.Text(),
        existing_nullable=True)
    op.alter_column('processing_jobs', 'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False)
    op.alter_column('processing_jobs', 'completed_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True)

    # Remove old columns from processing_jobs
    op.drop_index('ix_processing_jobs_id', table_name='processing_jobs')
    op.drop_constraint('processing_jobs_user_id_fkey', 'processing_jobs', type_='foreignkey')
    op.drop_column('processing_jobs', 'filename')
    op.drop_column('processing_jobs', 'original_filename')
    op.drop_column('processing_jobs', 'file_size')
    op.drop_column('processing_jobs', 'file_path')
    op.drop_column('processing_jobs', 'progress')
    op.drop_column('processing_jobs', 'extracted_data')
    op.drop_column('processing_jobs', 'hs_code_matches')
    op.drop_column('processing_jobs', 'xml_output')
    op.drop_column('processing_jobs', 'updated_at')

    # Add processing_jobs constraints
    op.create_check_constraint('positive_file_size', 'processing_jobs', 'input_file_size > 0')
    op.create_check_constraint('positive_credits_used', 'processing_jobs', 'credits_used >= 0')
    op.create_check_constraint('positive_total_products', 'processing_jobs', 'total_products >= 0')
    op.create_check_constraint('positive_successful_matches', 'processing_jobs', 'successful_matches >= 0')
    op.create_check_constraint('valid_confidence_range', 'processing_jobs', 'average_confidence >= 0 AND average_confidence <= 1')
    op.create_check_constraint('valid_country_schema', 'processing_jobs', 'length(country_schema) = 3')
    op.create_check_constraint('positive_processing_time', 'processing_jobs', 'processing_time_ms >= 0')
    op.create_check_constraint('positive_xml_file_size', 'processing_jobs', 'xml_file_size >= 0')
    op.create_check_constraint('valid_xml_generation_status', 'processing_jobs', 
        "xml_generation_status IN ('PENDING', 'GENERATING', 'COMPLETED', 'FAILED') OR xml_generation_status IS NULL")

    # Recreate foreign key with CASCADE
    op.create_foreign_key('fk_processing_jobs_user_id', 'processing_jobs', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # ===== OPTIMIZED INDEXES =====
    # Users indexes
    op.create_index('idx_users_email', 'users', ['email'], unique=True)
    op.create_index('idx_users_country', 'users', ['country'])
    op.create_index('idx_users_subscription_tier', 'users', ['subscription_tier'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])

    # HS Codes indexes
    op.create_index('idx_hs_codes_code', 'hs_codes', ['code'], unique=True)
    op.create_index('idx_hs_codes_country_active', 'hs_codes', ['country', 'is_active'], 
                    postgresql_where=sa.text('is_active = true'))

    # Processing Jobs indexes
    op.create_index('idx_processing_jobs_user_created', 'processing_jobs', ['user_id', 'created_at'])
    op.create_index('idx_processing_jobs_status', 'processing_jobs', ['status'])
    op.create_index('idx_processing_jobs_country', 'processing_jobs', ['country_schema'])

    # Product Matches indexes
    op.create_index('idx_product_matches_job_id', 'product_matches', ['job_id'])
    op.create_index('idx_product_matches_hs_code', 'product_matches', ['matched_hs_code'])
    op.create_index('idx_product_matches_confidence', 'product_matches', ['confidence_score'])

    # Billing Transactions indexes
    op.create_index('idx_billing_transactions_user_id', 'billing_transactions', ['user_id'])
    op.create_index('idx_billing_transactions_status', 'billing_transactions', ['status'])
    op.create_index('idx_billing_transactions_created', 'billing_transactions', ['created_at'])

    # Special JSONB index for embeddings
    op.execute('CREATE INDEX IF NOT EXISTS idx_hs_codes_embedding_gin ON hs_codes USING gin (embedding)')


def downgrade() -> None:
    # Drop specialized indexes
    op.execute('DROP INDEX IF EXISTS idx_hs_codes_embedding_gin')
    
    # Drop all custom indexes
    op.drop_index('idx_billing_transactions_created', table_name='billing_transactions')
    op.drop_index('idx_billing_transactions_status', table_name='billing_transactions')
    op.drop_index('idx_billing_transactions_user_id', table_name='billing_transactions')
    op.drop_index('idx_product_matches_confidence', table_name='product_matches')
    op.drop_index('idx_product_matches_hs_code', table_name='product_matches')
    op.drop_index('idx_product_matches_job_id', table_name='product_matches')
    op.drop_index('idx_processing_jobs_country', table_name='processing_jobs')
    op.drop_index('idx_processing_jobs_status', table_name='processing_jobs')
    op.drop_index('idx_processing_jobs_user_created', table_name='processing_jobs')
    op.drop_index('idx_hs_codes_country_active', table_name='hs_codes')
    op.drop_index('idx_hs_codes_code', table_name='hs_codes')
    op.drop_index('idx_users_created_at', table_name='users')
    op.drop_index('idx_users_subscription_tier', table_name='users')
    op.drop_index('idx_users_country', table_name='users')
    op.drop_index('idx_users_email', table_name='users')

    # Restore processing_jobs to original state
    op.drop_constraint('fk_processing_jobs_user_id', 'processing_jobs', type_='foreignkey')
    op.add_column('processing_jobs', sa.Column('updated_at', sa.DateTime(), nullable=False))
    op.add_column('processing_jobs', sa.Column('xml_output', sa.VARCHAR(), nullable=True))
    op.add_column('processing_jobs', sa.Column('hs_code_matches', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('processing_jobs', sa.Column('extracted_data', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('processing_jobs', sa.Column('file_path', sa.VARCHAR(), nullable=False))
    op.add_column('processing_jobs', sa.Column('file_size', sa.INTEGER(), nullable=False))
    op.add_column('processing_jobs', sa.Column('filename', sa.VARCHAR(), nullable=False))
    op.add_column('processing_jobs', sa.Column('original_filename', sa.VARCHAR(), nullable=False))
    op.add_column('processing_jobs', sa.Column('progress', sa.Float(), nullable=False))
    
    # Drop constraints and columns added in upgrade
    op.drop_constraint('valid_xml_generation_status', 'processing_jobs', type_='check')
    op.drop_constraint('positive_xml_file_size', 'processing_jobs', type_='check')
    op.drop_constraint('positive_processing_time', 'processing_jobs', type_='check')
    op.drop_constraint('valid_country_schema', 'processing_jobs', type_='check')
    op.drop_constraint('valid_confidence_range', 'processing_jobs', type_='check')
    op.drop_constraint('positive_successful_matches', 'processing_jobs', type_='check')
    op.drop_constraint('positive_total_products', 'processing_jobs', type_='check')
    op.drop_constraint('positive_credits_used', 'processing_jobs', type_='check')
    op.drop_constraint('positive_file_size', 'processing_jobs', type_='check')
    
    op.drop_column('processing_jobs', 'started_at')
    op.drop_column('processing_jobs', 'country_schema')
    op.drop_column('processing_jobs', 'average_confidence')
    op.drop_column('processing_jobs', 'successful_matches')
    op.drop_column('processing_jobs', 'total_products')
    op.drop_column('processing_jobs', 'processing_time_ms')
    op.drop_column('processing_jobs', 'credits_used')
    op.drop_column('processing_jobs', 'xml_file_size')
    op.drop_column('processing_jobs', 'xml_generated_at')
    op.drop_column('processing_jobs', 'xml_generation_status')
    op.drop_column('processing_jobs', 'output_xml_url')
    op.drop_column('processing_jobs', 'input_file_size')
    op.drop_column('processing_jobs', 'input_file_url')
    op.drop_column('processing_jobs', 'input_file_name')

    # Restore original processing_jobs columns
    op.alter_column('processing_jobs', 'completed_at',
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True)
    op.alter_column('processing_jobs', 'created_at',
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False)
    op.alter_column('processing_jobs', 'error_message',
        existing_type=sa.Text(),
        type_=sa.VARCHAR(),
        existing_nullable=True)
    
    op.create_foreign_key('processing_jobs_user_id_fkey', 'processing_jobs', 'users', ['user_id'], ['id'])
    op.create_index('ix_processing_jobs_id', 'processing_jobs', ['id'], unique=False)

    # Restore users to original state
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_constraint('valid_country_code', 'users', type_='check')
    op.drop_constraint('positive_credits_used', 'users', type_='check')
    op.drop_constraint('positive_credits', 'users', type_='check')
    
    op.add_column('users', sa.Column('name', sa.VARCHAR(), nullable=False))
    op.add_column('users', sa.Column('credits', sa.INTEGER(), nullable=False))
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    
    op.alter_column('users', 'created_at',
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False)
    
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'country')
    op.drop_column('users', 'company_name')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'credits_used_this_month')
    op.drop_column('users', 'credits_remaining')
    op.drop_column('users', 'subscription_tier')

    # Restore hs_codes to original state
    op.drop_constraint('valid_section_code', 'hs_codes', type_='check')
    op.drop_constraint('valid_chapter_code', 'hs_codes', type_='check')
    op.drop_constraint('valid_country_code', 'hs_codes', type_='check')
    
    op.add_column('hs_codes', sa.Column('units', sa.VARCHAR(), nullable=True))
    op.add_column('hs_codes', sa.Column('tariff_rate', sa.Float(), nullable=True))
    op.add_column('hs_codes', sa.Column('is_restricted', sa.VARCHAR(), nullable=True))
    op.add_column('hs_codes', sa.Column('category', sa.VARCHAR(), nullable=False))
    op.add_column('hs_codes', sa.Column('embedding_vector', sa.VARCHAR(), nullable=True))
    op.create_index('ix_hs_codes_code', 'hs_codes', ['code'], unique=True)
    
    op.alter_column('hs_codes', 'code',
        existing_type=sa.String(length=10),
        type_=sa.VARCHAR(length=10),
        existing_nullable=False)
    
    op.drop_column('hs_codes', 'updated_at')
    op.drop_column('hs_codes', 'is_active')
    op.drop_column('hs_codes', 'country')
    op.drop_column('hs_codes', 'embedding')
    op.drop_column('hs_codes', 'section')
    op.drop_column('hs_codes', 'chapter')

    # Drop new tables
    op.drop_table('product_matches')
    op.drop_table('billing_transactions')
    
    # Drop new enum types
    op.execute("DROP TYPE IF EXISTS subscriptiontier")