from connectors._base.schemas import RunArgs
from src.utils.config import Config


def test_default_tenant_slug_is_olist_retail():
    assert Config.DEFAULT_TENANT_SLUG == "olist-retail"


def test_run_args_defaults_to_config_tenant_slug():
    args = RunArgs()
    assert args.tenant_slug == Config.DEFAULT_TENANT_SLUG


def test_run_args_accepts_explicit_tenant_slug():
    args = RunArgs(tenant_slug="acme-coffee")
    assert args.tenant_slug == "acme-coffee"
