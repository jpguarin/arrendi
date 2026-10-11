"""owners, its row security policy and the database roles

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Roles are created without login and without a password: roles are global to the
    # server and a password here would be a secret in the repository. Each environment
    # enables login by hand (see docs/modelo-de-datos.md).
    op.execute(
        """
        do $$
        begin
          if not exists (select from pg_roles where rolname = 'arrendi_api') then
            create role arrendi_api nologin;
          end if;
          if not exists (select from pg_roles where rolname = 'arrendi_tasks') then
            create role arrendi_tasks nologin bypassrls;
          end if;
        end
        $$
        """
    )
    op.execute("grant usage on schema public to arrendi_api, arrendi_tasks")

    op.execute(
        """
        create function set_updated_at() returns trigger
        language plpgsql as $$
        begin
          new.updated_at = now();
          return new;
        end
        $$
        """
    )

    op.execute(
        """
        create table owners (
          id uuid primary key,
          name text not null,
          document_number text,
          email text not null,
          payment_details text,
          send_day smallint not null default 1,
          reminder_1 boolean not null default true,
          reminder_2 boolean not null default true,
          email_copy boolean not null default false,
          next_number integer not null default 1,
          data_consent_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint owners_send_day_check check (send_day between 1 and 28)
        )
        """
    )
    op.execute(
        """
        create trigger owners_set_updated_at
          before update on owners
          for each row execute function set_updated_at()
        """
    )

    # Row security. `force` applies it to the table owner too. When no owner is set the
    # setting is null (or empty, on a connection that set it before), and no row passes.
    op.execute("alter table owners enable row level security")
    op.execute("alter table owners force row level security")
    op.execute(
        """
        create policy owner_isolation on owners
          using (id = nullif(current_setting('app.owner_id', true), '')::uuid)
          with check (id = nullif(current_setting('app.owner_id', true), '')::uuid)
        """
    )

    # Minimum privileges. No role deletes owners.
    op.execute("grant select, insert, update on owners to arrendi_api")
    op.execute("grant select, update on owners to arrendi_tasks")

    # Supabase lets its Data API roles use every new table in `public`. Only FastAPI
    # reads Arrendi's tables, so take that away. The roles do not exist outside Supabase.
    op.execute(
        """
        do $$
        declare
          data_api_role text;
        begin
          foreach data_api_role in array array['anon', 'authenticated', 'service_role'] loop
            if exists (select from pg_roles where rolname = data_api_role) then
              execute format('revoke all on owners from %I', data_api_role);
            end if;
          end loop;
        end
        $$
        """
    )


def downgrade() -> None:
    # The roles stay: they are global to the server and other databases may use them.
    op.execute("drop table owners")
    op.execute("drop function set_updated_at()")
    op.execute("revoke usage on schema public from arrendi_api, arrendi_tasks")
