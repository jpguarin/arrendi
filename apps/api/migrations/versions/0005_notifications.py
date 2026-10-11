"""notifications, with their row security policy

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        create table notifications (
          id uuid primary key default gen_random_uuid(),
          owner_id uuid not null constraint notifications_owner_fk references owners (id),
          bill_id uuid not null,
          type text not null,
          channel text not null default 'email',
          recipient text not null,
          delivery_status text not null default 'pending',
          provider_id text,
          sent_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint notifications_bill_fk foreign key (owner_id, bill_id)
            references bills (owner_id, id),
          constraint notifications_type_check check (
            type in ('bill', 'reminder_1', 'reminder_2', 'receipt', 'manual_reminder', 'resend')
          ),
          constraint notifications_channel_check check (channel in ('email')),
          constraint notifications_delivery_status_check
            check (delivery_status in ('pending', 'sent', 'bounced', 'failed'))
        )
        """
    )
    # The automatic emails go out once per bill. The row is set aside before sending, so
    # this index is what keeps the daily task from sending twice.
    op.execute(
        """
        create unique index notifications_one_automatic_per_bill on notifications (bill_id, type)
          where type in ('bill', 'reminder_1', 'reminder_2')
        """
    )
    # The provider reports a bounce by its own id.
    op.execute("create index notifications_provider_id_idx on notifications (provider_id)")
    op.execute("create index notifications_bill_id_idx on notifications (bill_id)")

    op.execute(
        """
        create trigger notifications_set_updated_at
          before update on notifications
          for each row execute function set_updated_at()
        """
    )
    op.execute("alter table notifications enable row level security")
    op.execute("alter table notifications force row level security")
    op.execute(
        """
        create policy owner_isolation on notifications
          using (owner_id = nullif(current_setting('app.owner_id', true), '')::uuid)
          with check (owner_id = nullif(current_setting('app.owner_id', true), '')::uuid)
        """
    )
    # Both roles send email: the owner by hand, the daily task on its own.
    op.execute("grant select, insert, update on notifications to arrendi_api, arrendi_tasks")

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
              execute format('revoke all on notifications from %I', data_api_role);
            end if;
          end loop;
        end
        $$
        """
    )


def downgrade() -> None:
    op.execute("drop table notifications")
