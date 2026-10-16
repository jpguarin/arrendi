"""lease cc emails: others who get every email of the tenant, in copy

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Up to three addresses that get, in plain sight, every email the tenant gets. Empty
    # for every lease that exists.
    op.execute(
        """
        alter table leases
          add column cc_emails text[] not null default '{}',
          add constraint leases_cc_emails_check check (cardinality(cc_emails) <= 3)
        """
    )


def downgrade() -> None:
    op.execute("alter table leases drop column cc_emails")
