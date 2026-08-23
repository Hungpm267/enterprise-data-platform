from unittest.mock import MagicMock, patch

from src.web.api.v1.analytics import _caller_tenant_slug


def _user(tenant_id, slug=None, role="client"):
    user = MagicMock()
    user.tenant_id = tenant_id
    user.tenant = MagicMock(slug=slug) if slug else None
    user.role = role
    return user


def test_client_user_resolves_to_their_tenant_slug():
    assert _caller_tenant_slug(_user("uuid-1", "acme-coffee")) == "acme-coffee"


def test_platform_admin_resolves_to_none():
    assert _caller_tenant_slug(_user(None, role="platform_admin")) is None


def test_user_with_tenant_id_but_missing_tenant_row_is_denied_not_escalated():
    # A dangling tenant_id must NOT silently fall through to unfiltered admin access.
    assert _caller_tenant_slug(_user("uuid-orphan", None)) == "__no_tenant__"


def test_null_tenant_id_without_admin_role_is_denied_not_escalated():
    # A null tenant_id alone must NOT be enough for unfiltered access — the
    # caller must also be a platform_admin. A non-admin with a null tenant_id
    # (should not normally occur, but must never escalate if it does) is
    # denied via the safe sentinel, never resolved to None.
    assert _caller_tenant_slug(_user(None, role="client")) == "__no_tenant__"
