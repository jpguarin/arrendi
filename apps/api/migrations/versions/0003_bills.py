"""bills and bill_items, with their row security policies

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("bills", "bill_items")


def upgrade() -> None:
    # Same shape as 0002: `unique (owner_id, id)` on the table others point to, and
    # composite foreign keys that carry the owner, because foreign keys skip row security.
    op.execute(
        """
        create table bills (
          id uuid primary key default gen_random_uuid(),
          owner_id uuid not null constraint bills_owner_fk references owners (id),
          lease_id uuid not null,
          number integer not null,
          origin text not null,
          period date,
          issue_date date not null,
          due_date date not null,
          total bigint not null,
          status text not null default 'pending',
          pdf_path text not null,
          voided_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint bills_owner_id_id_key unique (owner_id, id),
          constraint bills_owner_id_number_key unique (owner_id, number),
          constraint bills_lease_fk foreign key (owner_id, lease_id)
            references leases (owner_id, id),
          constraint bills_number_check check (number > 0),
          constraint bills_origin_check check (origin in ('monthly', 'manual')),
          constraint bills_period_check check (
            (origin = 'monthly') = (period is not null)
            and (period is null or extract(day from period) = 1)
          ),
          constraint bills_total_check check (total > 0),
          constraint bills_status_check
            check (status in ('pending', 'partial', 'paid', 'overdue', 'voided')),
          constraint bills_voided_at_check check ((status = 'voided') = (voided_at is not null))
        )
        """
    )
    op.execute(
        """
        create table bill_items (
          id uuid primary key default gen_random_uuid(),
          owner_id uuid not null constraint bill_items_owner_fk references owners (id),
          bill_id uuid not null,
          description text not null,
          amount bigint not null,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint bill_items_bill_fk foreign key (owner_id, bill_id)
            references bills (owner_id, id),
          constraint bill_items_amount_check check (amount > 0)
        )
        """
    )
    # One monthly bill per lease and period, unless it was voided. The database decides who
    # wins when two requests (or the daily task twice) generate the same month at once.
    op.execute(
        """
        create unique index bills_one_monthly_per_period on bills (lease_id, period)
          where origin = 'monthly' and status <> 'voided'
        """
    )
    # For the daily task, which looks for unpaid bills past their due date.
    op.execute("create index bills_status_due_date_idx on bills (status, due_date)")
    # The foreign keys are used to join; Postgres does not index them on its own.
    op.execute("create index bills_lease_id_idx on bills (lease_id)")
    op.execute("create index bill_items_bill_id_idx on bill_items (bill_id)")

    for table in TABLES:
        op.execute(
            f"""
            create trigger {table}_set_updated_at
              before update on {table}
              for each row execute function set_updated_at()
            """
        )
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"alter table {table} force row level security")
        op.execute(
            f"""
            create policy owner_isolation on {table}
              using (owner_id = nullif(current_setting('app.owner_id', true), '')::uuid)
              with check (owner_id = nullif(current_setting('app.owner_id', true), '')::uuid)
            """
        )

    # Minimum privileges. No role deletes: a bill is voided, it is not removed. The daily
    # task generates bills and marks them overdue; an issued bill's items never change.
    op.execute("grant select, insert, update on bills to arrendi_api")
    op.execute("grant select, insert on bill_items to arrendi_api")
    op.execute("grant select, insert, update on bills to arrendi_tasks")
    op.execute("grant select, insert on bill_items to arrendi_tasks")

    # Supabase lets its Data API roles use every new table in `public`. Only FastAPI reads
    # Arrendi's tables, so take that away. The roles do not exist outside Supabase.
    op.execute(
        """
        do $$
        declare
          data_api_role text;
          arrendi_table text;
        begin
          foreach data_api_role in array array['anon', 'authenticated', 'service_role'] loop
            if exists (select from pg_roles where rolname = data_api_role) then
              foreach arrendi_table in array array['bills', 'bill_items'] loop
                execute format('revoke all on %I from %I', arrendi_table, data_api_role);
              end loop;
            end if;
          end loop;
        end
        $$
        """
    )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"drop table {table}")
