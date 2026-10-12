"""payments, with their row security policy

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        create table payments (
          id uuid primary key default gen_random_uuid(),
          owner_id uuid not null constraint payments_owner_fk references owners (id),
          bill_id uuid not null,
          payment_date date not null,
          amount bigint not null,
          method text not null,
          proof_path text,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint payments_bill_fk foreign key (owner_id, bill_id)
            references bills (owner_id, id),
          constraint payments_amount_check check (amount > 0),
          constraint payments_method_check
            check (method in ('transfer', 'nequi', 'cash', 'other'))
        )
        """
    )
    # The balance of a bill is its total minus the sum of these.
    op.execute("create index payments_bill_id_idx on payments (bill_id)")

    op.execute(
        """
        create trigger payments_set_updated_at
          before update on payments
          for each row execute function set_updated_at()
        """
    )
    op.execute("alter table payments enable row level security")
    op.execute("alter table payments force row level security")
    op.execute(
        """
        create policy owner_isolation on payments
          using (owner_id = nullif(current_setting('app.owner_id', true), '')::uuid)
          with check (owner_id = nullif(current_setting('app.owner_id', true), '')::uuid)
        """
    )
    # The only table where a role deletes: a payment entered by mistake is removed. The
    # daily task only reads them, for the balance its reminders mention.
    op.execute("grant select, insert, update, delete on payments to arrendi_api")
    op.execute("grant select on payments to arrendi_tasks")

    # Supabase lets its Data API roles use every new table in `public`. Only FastAPI reads
    # Arrendi's tables, so take that away. The roles do not exist outside Supabase.
    op.execute(
        """
        do $$
        declare
          data_api_role text;
        begin
          foreach data_api_role in array array['anon', 'authenticated', 'service_role'] loop
            if exists (select from pg_roles where rolname = data_api_role) then
              execute format('revoke all on payments from %I', data_api_role);
            end if;
          end loop;
        end
        $$
        """
    )


def downgrade() -> None:
    op.execute("drop table payments")
