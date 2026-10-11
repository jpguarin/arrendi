"""owners.document_type: whether the owner's document is a cédula or a NIT

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A small landlord is almost always a person, so the cédula is the starting point.
    op.execute(
        """
        alter table owners
          add column document_type text not null default 'cc',
          add constraint owners_document_type_check check (document_type in ('cc', 'nit'))
        """
    )


def downgrade() -> None:
    op.execute("alter table owners drop column document_type")
