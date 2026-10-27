from sqlalchemy.engine.url import make_url

from src.utils.config import Config


def test_db_url_pins_psycopg2_driver():
    """SQLAlchemy 2.1 changed the default PostgreSQL driver from psycopg2 to
    psycopg (v3). A bare postgresql:// URL then fails on fresh installs with
    ModuleNotFoundError: psycopg, so the driver must be explicit."""
    url = make_url(Config.get_db_url())
    assert url.drivername == "postgresql+psycopg2"
