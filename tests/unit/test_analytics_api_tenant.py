from unittest.mock import MagicMock, patch

from src.web.api.v1.analytics import _caller_tenant_slug


def _user(tenant_id, slug=None):
    user = MagicMock()
    user.tenant_id = tenant_id
    user.tenant = MagicMock(slug=slug) if slug else None
    return user


def test_client_user_resolves_to_their_tenant_slug():
    assert _caller_tenant_slug(_user("uuid-1", "acme-coffee")) == "acme-coffee"


def test_platform_admin_resolves_to_none():
    assert _caller_tenant_slug(_user(None)) is None


def test_user_with_tenant_id_but_missing_tenant_row_is_denied_not_escalated():
    # A dangling tenant_id must NOT silently fall through to unfiltered admin access.
    assert _caller_tenant_slug(_user("uuid-orphan", None)) == "__no_tenant__"
