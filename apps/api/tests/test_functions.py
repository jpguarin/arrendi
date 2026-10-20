"""The functions of `public` resolve names only in `pg_catalog`, whoever calls them."""

from sqlalchemy import Engine, text


def test_set_updated_at_has_an_empty_search_path(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        config = connection.execute(
            text(
                "select proconfig from pg_proc "
                "where proname = 'set_updated_at' and pronamespace = 'public'::regnamespace"
            )
        ).scalar_one()

    assert config == ['search_path=""']
