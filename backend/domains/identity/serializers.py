"""Serialisasi bentuk respons kontrak frontend (contracts.ts)."""
from __future__ import annotations

from domains.identity.services import AuthContext


def session_user(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "mfa_enabled": user.mfa_enabled,
        "platform_admin": bool(user.platform_admin),
    }


def auth_context(ctx: AuthContext) -> dict:
    return {
        "user": session_user(ctx.user),
        "tenants": ctx.tenants,
        "active_tenant_id": ctx.active_tenant_id,
        "permissions": ctx.permissions,
        "sensitive_reauth_until": ctx.sensitive_reauth_until,
    }
