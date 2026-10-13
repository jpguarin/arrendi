"""lease_items: what a lease charges every month besides the rent

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Same shape as the other tables: the foreign key carries the owner, because foreign
    # keys skip row security.
    op.execute(
        """
        create table lease_items (
          id uuid primary key default gen_random_uuid(),
          owner_id uuid not null constraint lease_items_owner_fk references owners (id),
          lease_id uuid not null,
          description text not null,
          amount bigint not null,
          position smallint not null,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint lease_items_lease_fk foreign key (owner_id, lease_id)
            references leases (owner_id, id),
          constraint lease_items_amount_check check (amount > 0),
          constraint lease_items_position_check check (position >= 0),
          -- The order the bill shows them in; it also finds the items of a lease.
          constraint lease_items_lease_id_position_key unique (lease_id, position)
        )
        """
    )

    op.execute(
        """
        create trigger lease_items_set_updated_at
          before update on lease_items
          for each row execute function set_updated_at()
        """
    )
    op.execute("alter table lease_items enable row level security")
    op.execute("alter table lease_items force row level security")
    op.execute(
        """
        create policy owner_isolation on lease_items
          using (owner_id = nullif(current_setting('app.owner_id', true), '')::uuid)
          with check (owner_id = nullif(current_setting('app.owner_id', true), '')::uuid)
        """
    )
    # Editing a lease replaces its whole list, so the API deletes and inserts, and never
    # updates. What was already billed lives in `bill_items`, which nothing here touches.
    # The daily task only reads them, to issue the bill of the month.
    op.execute("grant select, insert, delete on lease_items to arrendi_api")
    op.execute("grant select on lease_items to arrendi_tasks")

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
              execute format('revoke all on lease_items from %I', data_api_role);
            end if;
          end loop;
        end
        $$
        """
    )


def downgrade() -> None:
    op.execute("drop table lease_items")
