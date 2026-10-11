from uuid import UUID

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app.db import set_owner_id


def test_updated_at_changes_on_update(api_engine: Engine, two_owners: tuple[UUID, UUID]) -> None:
    ana, _ = two_owners

    with api_engine.begin() as connection:
        set_owner_id(connection, ana)
        connection.execute(text("update owners set name = 'Ana María' where id = :id"), {"id": ana})
        row = connection.execute(text("select created_at, updated_at from owners")).one()

    assert row.updated_at > row.created_at


@pytest.mark.parametrize("send_day", [0, 29])
def test_send_day_must_be_between_1_and_28(
    api_engine: Engine, two_owners: tuple[UUID, UUID], send_day: int
) -> None:
    ana, _ = two_owners

    with pytest.raises(IntegrityError, match="owners_send_day_check"), api_engine.begin() as conn:
        set_owner_id(conn, ana)
        conn.execute(text("update owners set send_day = :day"), {"day": send_day})
