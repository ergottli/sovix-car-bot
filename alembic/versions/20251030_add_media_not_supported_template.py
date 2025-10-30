"""Add media_not_supported_text template

Revision ID: 002_add_media_template
Revises: 001_add_status
Create Date: 2025-10-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_media_template'
down_revision = '001_add_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add media_not_supported_text template to text_templates table."""
    op.execute("""
        INSERT INTO text_templates (key, value, description)
        VALUES (
            'media_not_supported_text', 
            'Напишите свой вопрос. Картинки и аудио я пока не понимаю, но уже учусь)',
            'Сообщение при получении картинок, аудио или других медиафайлов'
        )
        ON CONFLICT (key) DO UPDATE 
        SET value = EXCLUDED.value, updated_at = NOW()
    """)
    print("✅ Added 'media_not_supported_text' template to text_templates table")


def downgrade() -> None:
    """Remove media_not_supported_text template from text_templates table."""
    op.execute("""
        DELETE FROM text_templates 
        WHERE key = 'media_not_supported_text'
    """)
    print("✅ Removed 'media_not_supported_text' template from text_templates table")

