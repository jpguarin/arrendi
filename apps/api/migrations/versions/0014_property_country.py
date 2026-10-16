"""property country: where the property is, as a code of ISO 3166-1

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Every property that exists is in Colombia. The API checks that the code exists;
    # the database, that it has the shape of one.
    op.execute(
        """
        alter table properties
          add column country text not null default 'CO',
          add constraint properties_country_check check (country ~ '^[A-Z]{2}$')
        """
    )


def downgrade() -> None:
    op.execute("alter table properties drop column country")
