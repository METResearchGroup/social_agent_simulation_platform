import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from db.adapters.sqlite.sqlite import DB_PATH
from db.schema import metadata as target_metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging (only when an .ini file exists).
# When using pyproject.toml exclusively there is no .ini; skip fileConfig.
if config.config_file_name is not None and os.path.isfile(config.config_file_name):
    fileConfig(config.config_file_name)


def _get_sqlalchemy_url() -> str:
    """Return the SQLAlchemy URL used for migrations.

    Precedence:
    - SIM_DATABASE_URL: full SQLAlchemy URL (e.g. sqlite:////abs/path/db.sqlite)
    - SIM_DB_PATH: filesystem path to sqlite file
    - DB_PATH: default sqlite file used by the application
    """

    database_url = os.environ.get("SIM_DATABASE_URL")
    if database_url:
        return database_url

    db_path = os.environ.get("SIM_DB_PATH", DB_PATH)
    if db_path.startswith("sqlite:"):
        # Defensive: allow passing a URL in SIM_DB_PATH by accident.
        return db_path

    # DB_PATH is an absolute path; sqlite:/// + /abs/path => sqlite:////abs/path
    return f"sqlite:///{db_path}"


# Ensure `config.get_main_option("sqlalchemy.url")` has a meaningful value.
config.set_main_option("sqlalchemy.url", _get_sqlalchemy_url())

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = config.get_main_option("sqlalchemy.url")
    assert url is not None, "sqlalchemy.url must be set by set_main_option"
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
