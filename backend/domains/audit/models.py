"""Audit event — aktor, target, aksi, payload tersanitasi (TK-102).

Payload disaring: password, token, secret, dan isi file tidak pernah masuk
audit. Tabel tenant-scoped + RLS.
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone as dj_timezone

REDACTED_KEYS = {
    "password",
    "password_hash",
    "token",
    "secret",
    "shared_secret",
    "seed",
    "encrypted_seed",
    "recovery_codes",
    "totp_code",
    "credential",
    "private_key",
}


def redact(payload: dict | None) -> dict:
    """Salin payload dengan menyunting kunci sensitif (redaction §3/§7)."""
    if not isinstance(payload, dict):
        return {}
    cleaned: dict = {}
    for key, value in payload.items():
        if any(marker in str(key).lower() for marker in REDACTED_KEYS):
            cleaned[key] = "[redacted]"
        elif isinstance(value, dict):
            cleaned[key] = redact(value)
        else:
            cleaned[key] = value
    return cleaned


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="audit_events", db_column="tenant_id")
    actor_display = models.CharField(max_length=120, blank=True, default="")
    actor_id = models.UUIDField(null=True, blank=True)
    action_code = models.CharField(max_length=64)
    target_type = models.CharField(max_length=48, blank=True, default="")
    target_id = models.CharField(max_length=64, blank=True, default="")
    target_display = models.CharField(max_length=160, blank=True, default="")
    payload = models.JSONField(default=dict)
    request_id = models.CharField(max_length=32, blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now, db_index=True)

    class Meta:
        db_table = "audit_event"
        indexes = [
            models.Index(fields=["tenant", "created_at", "id"], name="ix_audit_tenant_time"),
            models.Index(fields=["tenant", "target_type", "target_id"], name="ix_audit_tenant_target"),
        ]


def record(
    *,
    tenant_id,
    action_code: str,
    actor_display: str = "",
    actor_id=None,
    target_type: str = "",
    target_id: str = "",
    target_display: str = "",
    payload: dict | None = None,
    request_id: str = "",
) -> AuditEvent:
    return AuditEvent.objects.create(
        tenant_id=tenant_id,
        action_code=action_code,
        actor_display=actor_display,
        actor_id=actor_id,
        target_type=target_type,
        target_id=str(target_id or ""),
        target_display=target_display[:160],
        payload=redact(payload),
        request_id=request_id[:32],
    )
