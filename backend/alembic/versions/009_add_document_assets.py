"""009 add document assets

Revision ID: 009
Revises: 008
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("stored_filename", sa.String(length=260), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("image", "video", "file", name="assetkind"), nullable=False),
        sa.Column("storage_path", sa.String(length=800), nullable=False),
        sa.Column("public_path", sa.String(length=800), nullable=False),
        sa.Column("uploaded_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_assets_version_id"), "document_assets", ["version_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_assets_version_id"), table_name="document_assets")
    op.drop_table("document_assets")
    sa.Enum("image", "video", "file", name="assetkind").drop(op.get_bind(), checkfirst=True)
