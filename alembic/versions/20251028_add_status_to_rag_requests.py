"""Add status column to rag_requests table

Revision ID: 001_add_status
Revises: 
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_status'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add status column to rag_requests table."""
    # Check if column already exists to avoid errors
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name='rag_requests' AND column_name='status'
        )
    """))
    exists = result.scalar()
    
    if not exists:
        # Add status column
        op.execute("""
            ALTER TABLE rag_requests 
            ADD COLUMN status TEXT DEFAULT 'pending'
        """)
        
        # Update existing records to have 'success' status
        op.execute("""
            UPDATE rag_requests 
            SET status = 'success' 
            WHERE status IS NULL
        """)
        
        print("✅ Added 'status' column to rag_requests table")
    else:
        print("ℹ️  Column 'status' already exists in rag_requests table")


def downgrade() -> None:
    """Remove status column from rag_requests table."""
    op.execute("""
        ALTER TABLE rag_requests 
        DROP COLUMN IF EXISTS status
    """)
    print("✅ Removed 'status' column from rag_requests table")

