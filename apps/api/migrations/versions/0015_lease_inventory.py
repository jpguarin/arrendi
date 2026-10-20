"""lease inventory: a second file of the lease, next to the signed lease

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        alter table leases
          add column inventory_path text,
          add column inventory_uploaded_at timestamptz
        """
    )


def downgrade() -> None:
    op.execute("alter table leases drop column inventory_uploaded_at, drop column inventory_path")
