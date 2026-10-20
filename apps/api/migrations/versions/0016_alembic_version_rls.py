"""alembic_version: row security and no Data API access, like every other table

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Alembic creates this table on its own, in `public`, so Supabase's Data API could read
    # and change it. Row security without policies closes it. It is not forced: the owner
    # runs the migrations and keeps writing the version.
    op.execute("alter table alembic_version enable row level security")

    # The roles do not exist outside Supabase.
    op.execute(
        """
        do $$
        declare
          data_api_role text;
        begin
          foreach data_api_role in array array['anon', 'authenticated', 'service_role'] loop
            if exists (select from pg_roles where rolname = data_api_role) then
              execute format('revoke all on alembic_version from %I', data_api_role);
            end if;
          end loop;
        end
        $$
        """
    )


def downgrade() -> None:
    # The revoked privileges stay revoked: nothing should give them back.
    op.execute("alter table alembic_version disable row level security")
