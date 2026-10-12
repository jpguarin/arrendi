"""leases.payment_details and bills.payment_details: how to pay, per lease and per bill

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The owner's payment details are the default. A lease may have its own, and a bill
    # keeps the ones it was issued with, so nothing that changes later reaches it.
    op.execute("alter table leases add column payment_details text")
    op.execute("alter table bills add column payment_details text")
    # Bills issued before this read the owner's every time; they keep what is there now.
    # Row security is forced, and with no owner set it would hide every row from this
    # update unless the role bypasses it. Lifting it for the statement does not depend on that.
    tables = ("bills", "owners")
    for table in tables:
        op.execute(f"alter table {table} no force row level security")
    op.execute(
        """
        update bills
           set payment_details = owners.payment_details
          from owners
         where owners.id = bills.owner_id
        """
    )
    for table in tables:
        op.execute(f"alter table {table} force row level security")


def downgrade() -> None:
    op.execute("alter table bills drop column payment_details")
    op.execute("alter table leases drop column payment_details")
