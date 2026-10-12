"""leases.charge_deposit and bill_items.position: the deposit as an item of the first bill

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Whether the first monthly bill of the lease charges its deposit. False here, so the
    # leases that already exist, whose deposit was settled outside Arrendi, are never
    # charged for it; the API turns it on for the new ones unless the owner says no.
    op.execute("alter table leases add column charge_deposit boolean not null default false")
    # A bill may now have several items, all created in the same instant: this is their order.
    op.execute("alter table bill_items add column position smallint not null default 0")


def downgrade() -> None:
    op.execute("alter table bill_items drop column position")
    op.execute("alter table leases drop column charge_deposit")
