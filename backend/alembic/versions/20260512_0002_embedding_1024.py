"""set embedding vector dimension to 1024

Revision ID: 20260512_0002
Revises: 20260512_0001
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
from alembic import op

revision: str = "20260512_0002"
down_revision: str | None = "20260512_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "document_chunks",
        "embedding",
        type_=pgvector.sqlalchemy.Vector(1024),
        postgresql_using="embedding::vector(1024)",
    )


def downgrade() -> None:
    op.alter_column(
        "document_chunks",
        "embedding",
        type_=pgvector.sqlalchemy.Vector(),
        postgresql_using="embedding::vector",
    )

