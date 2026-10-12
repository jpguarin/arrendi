"""tenants.document_type: whether the tenant's document is a cédula or a NIT

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Same as the owner's (0004). A home is rented by a person, so the cédula is the
    # starting point; a shop is often rented by a company with a NIT.
    op.execute(
        """
        alter table tenants
          add column document_type text not null default 'cc',
          add constraint tenants_document_type_check check (document_type in ('cc', 'nit'))
        """
    )


def downgrade() -> None:
    op.execute("alter table tenants drop column document_type")
