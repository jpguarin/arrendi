"""late fees: the lease's terms, the bill's own, and the item that charges one

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # What the lease says about paying late: a percentage of the rent, charged once, after
    # some days of grace. Off for every lease that exists.
    op.execute(
        """
        alter table leases
          add column late_fee_enabled boolean not null default false,
          add column late_fee_percent numeric(5, 2),
          add column late_fee_grace_days smallint not null default 0,
          add constraint leases_late_fee_percent_check
            check (late_fee_percent is null or (late_fee_percent > 0 and late_fee_percent <= 100)),
          add constraint leases_late_fee_grace_days_check
            check (late_fee_grace_days between 0 and 30),
          add constraint leases_late_fee_enabled_check
            check (not late_fee_enabled or late_fee_percent is not null)
        """
    )
    # A monthly bill keeps the terms it was issued with: how much paying late costs and
    # from what day. Null in the bills issued without a late fee, which never owe one.
    # The owner may waive it, bill by bill.
    op.execute(
        """
        alter table bills
          add column late_fee_amount bigint,
          add column late_fee_deadline date,
          add column late_fee_waived_at timestamptz,
          add constraint bills_late_fee_check
            check (
              (late_fee_amount is null) = (late_fee_deadline is null)
              and (late_fee_amount is null or late_fee_amount > 0)
              and (late_fee_waived_at is null or late_fee_amount is not null)
            )
        """
    )
    # The fee is never added to the late bill, which is not edited: it is an item of a
    # later bill, and this says which late bill it is for. The foreign key carries the
    # owner, like the others, because foreign keys skip row security.
    op.execute(
        """
        alter table bill_items
          add column late_fee_of_bill_id uuid,
          add constraint bill_items_late_fee_fk foreign key (owner_id, late_fee_of_bill_id)
            references bills (owner_id, id)
        """
    )
    op.execute(
        """
        create index bill_items_late_fee_of_bill_id_idx on bill_items (late_fee_of_bill_id)
          where late_fee_of_bill_id is not null
        """
    )


def downgrade() -> None:
    op.execute("alter table bill_items drop column late_fee_of_bill_id")
    op.execute(
        """
        alter table bills
          drop column late_fee_amount,
          drop column late_fee_deadline,
          drop column late_fee_waived_at
        """
    )
    op.execute(
        """
        alter table leases
          drop column late_fee_enabled,
          drop column late_fee_percent,
          drop column late_fee_grace_days
        """
    )
