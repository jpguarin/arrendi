"""owners.signature_path and bills.signature_path: the owner's signature on the bill

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The image the owner signs with, in the private bucket. A bill keeps the one it was
    # issued with, so changing or removing the owner's later does not reach it. The bills
    # issued before this have none.
    op.execute("alter table owners add column signature_path text")
    op.execute("alter table bills add column signature_path text")


def downgrade() -> None:
    op.execute("alter table bills drop column signature_path")
    op.execute("alter table owners drop column signature_path")
