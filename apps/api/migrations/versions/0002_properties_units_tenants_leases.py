"""properties, units, tenants and leases, with their row security policies

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("properties", "units", "tenants", "leases")


def upgrade() -> None:
    # Every table that others point to has `unique (owner_id, id)`, and every foreign key
    # is composite and carries the owner. Foreign keys skip row security, so a plain
    # `property_id` would let an owner point at another owner's row by knowing its id.
    op.execute(
        """
        create table properties (
          id uuid primary key default gen_random_uuid(),
          owner_id uuid not null constraint properties_owner_fk references owners (id),
          name text not null,
          address text,
          city text,
          type text not null,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint properties_owner_id_id_key unique (owner_id, id),
          constraint properties_type_check
            check (type in ('house', 'building', 'apartment', 'shop'))
        )
        """
    )
    op.execute(
        """
        create table units (
          id uuid primary key default gen_random_uuid(),
          owner_id uuid not null constraint units_owner_fk references owners (id),
          property_id uuid not null,
          name text not null,
          use text not null,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint units_owner_id_id_key unique (owner_id, id),
          constraint units_property_fk foreign key (owner_id, property_id)
            references properties (owner_id, id),
          constraint units_use_check check (use in ('residential', 'commercial'))
        )
        """
    )
    op.execute(
        """
        create table tenants (
          id uuid primary key default gen_random_uuid(),
          owner_id uuid not null constraint tenants_owner_fk references owners (id),
          name text not null,
          document_number text,
          email text not null,
          phone text,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint tenants_owner_id_id_key unique (owner_id, id)
        )
        """
    )
    op.execute(
        """
        create table leases (
          id uuid primary key default gen_random_uuid(),
          owner_id uuid not null constraint leases_owner_fk references owners (id),
          unit_id uuid not null,
          tenant_id uuid not null,
          rent bigint not null,
          due_day smallint not null,
          start_date date not null,
          end_date date,
          deposit bigint,
          status text not null default 'active',
          auto_send boolean not null default true,
          document_path text,
          document_uploaded_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint leases_owner_id_id_key unique (owner_id, id),
          constraint leases_unit_fk foreign key (owner_id, unit_id)
            references units (owner_id, id),
          constraint leases_tenant_fk foreign key (owner_id, tenant_id)
            references tenants (owner_id, id),
          constraint leases_rent_check check (rent > 0),
          constraint leases_due_day_check check (due_day between 1 and 28),
          constraint leases_dates_check check (end_date is null or end_date > start_date),
          constraint leases_deposit_check check (deposit is null or deposit >= 0),
          constraint leases_status_check check (status in ('active', 'ended'))
        )
        """
    )
    # The database, not the code, decides who wins when two requests create a lease for the
    # same unit at once.
    op.execute(
        """
        create unique index leases_one_active_per_unit on leases (unit_id)
          where status = 'active'
        """
    )
    # The foreign keys are used to join; Postgres does not index them on its own.
    op.execute("create index units_property_id_idx on units (property_id)")
    op.execute("create index leases_tenant_id_idx on leases (tenant_id)")

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
        # Minimum privileges. No role deletes: a lease ends, it is not removed.
        op.execute(f"grant select, insert, update on {table} to arrendi_api")
        op.execute(f"grant select on {table} to arrendi_tasks")

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
              foreach arrendi_table in array
                array['properties', 'units', 'tenants', 'leases'] loop
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
