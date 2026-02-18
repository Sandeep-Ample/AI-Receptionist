"""Add email and approval columns for auth system

Revision ID: auth_email_001
Revises: 66d43f4efb2b
Create Date: 2026-02-18 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'auth_email_001'
down_revision: Union[str, None] = '66d43f4efb2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add email column (unique) for user identification
    op.add_column('user_memory', sa.Column('email', sa.String(length=255), nullable=True))
    op.create_index('idx_user_memory_email', 'user_memory', ['email'], unique=True)
    
    # Add approval status fields
    op.add_column('user_memory', sa.Column('is_approved', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('user_memory', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user_memory', sa.Column('password_hash', sa.String(length=255), nullable=True))
    
    # Create partial index for approved users (raw SQL for PostgreSQL-specific syntax)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_memory_approved 
        ON user_memory(is_approved) 
        WHERE is_approved = TRUE
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_user_memory_approved")
    op.drop_column('user_memory', 'password_hash')
    op.drop_column('user_memory', 'approved_at')
    op.drop_column('user_memory', 'is_approved')
    op.drop_index('idx_user_memory_email', 'user_memory')
    op.drop_column('user_memory', 'email')
