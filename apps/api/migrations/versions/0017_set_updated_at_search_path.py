"""set_updated_at: a fixed, empty search_path

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Without it, the function resolves names with the search_path of whoever fires the
    # trigger. It only calls `now()`, and `pg_catalog` is always searched, so empty is enough.
    op.execute("alter function public.set_updated_at() set search_path = ''")


def downgrade() -> None:
    op.execute("alter function public.set_updated_at() reset search_path")
