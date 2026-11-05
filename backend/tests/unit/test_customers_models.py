"""Unit domain customers — validasi username, transisi state, validasi CSV (M4)."""
from __future__ import annotations

import pytest

from domains.common.envelope import ApiError
from domains.common.tenant_context import tenant_scope

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Validasi username (RADIUS.md §3)


class TestValidateUsername:
    def test_valid_plain(self):
        from domains.customers.services import validate_username

        assert validate_username("budi.santoso") == "budi.santoso"

    def test_valid_unicode_within_byte_budget(self):
        from domains.customers.services import validate_username

        # 20 karakter × 3 byte UTF-8 = 60 byte ≤ 64 — sah, tidak ditrim.
        username = "あ" * 20
        assert validate_username(username) == username
        assert len(username.encode("utf-8")) == 60

    def test_required(self):
        from domains.customers.services import validate_username

        for empty in ("", None, 42):
            with pytest.raises(ApiError) as exc:
                validate_username(empty)
            assert exc.value.status_code == 422
            assert exc.value.field_errors["username"][0]["code"] == "required"

    def test_leading_trailing_space_rejected_not_trimmed(self):
        from domains.customers.services import validate_username

        # Tidak ditrim diam-diam — ditolak (RADIUS §3: spasi tepi dilarang).
        with pytest.raises(ApiError) as exc:
            validate_username(" budi")
        assert exc.value.field_errors["username"][0]["code"] == "whitespace"
        with pytest.raises(ApiError):
            validate_username("budi ")

    def test_max_chars(self):
        from domains.customers.services import validate_username

        with pytest.raises(ApiError) as exc:
            validate_username("a" * 65)
        assert exc.value.field_errors["username"][0]["code"] == "max_length"

    def test_max_utf8_bytes(self):
        from domains.customers.services import validate_username

        # 22 karakter × 3 byte = 66 byte > 64 → ditolak walau jumlah karakter ≤64.
        with pytest.raises(ApiError) as exc:
            validate_username("あ" * 22)
        assert exc.value.field_errors["username"][0]["code"] == "max_length"

    def test_control_chars_rejected(self):
        from domains.customers.services import validate_username

        # Karakter kontrol bukan-spasi-tepi (spasi tepi ditangani whitespace):
        for bad in ("bu\tdi", "bu\x00di", "budi\x7f", "bu\x1fdi"):
            with pytest.raises(ApiError) as exc:
                validate_username(bad)
            assert exc.value.field_errors["username"][0]["code"] == "control_char"

    def test_case_sensitive_not_lowercased(self):
        from domains.customers.services import validate_username

        # Dibanding persis; tidak di-lowercase (namespace per tenant §3).
        assert validate_username("Budi.Santoso") == "Budi.Santoso"


# ---------------------------------------------------------------------------
# Validasi baris CSV mode create (tanpa DB)


class TestCsvCreateRowValidation:
    def _run(self, rows):
        from domains.customers.services import _validate_create_rows

        return _validate_create_rows("00000000-0000-0000-0000-000000000000", rows)

    def test_good_rows(self):
        rows = [
            {"username": "budi", "password": "rahasia-123", "kind": "pppoe", "package": "20M"},
            {"username": "siti", "kind": "hotspot", "customer_name": "Siti"},
        ]
        valid_idx, errors = self._run(rows)
        assert valid_idx == [0, 1]
        assert errors == []

    def test_missing_username(self):
        valid_idx, errors = self._run([{"package": "20M"}, {"username": "budi"}])
        assert valid_idx == [1]
        assert len(errors) == 1
        assert errors[0]["row"] == 2  # baris 1 = header (paritas mock)
        assert errors[0]["field"] == "username"
        assert errors[0]["reason_code"] == "required"
        assert errors[0]["action_hint"]

    def test_bad_kind(self):
        _, errors = self._run([{"username": "budi", "kind": "l2tp"}])
        assert errors[0]["reason_code"] == "choice"
        assert errors[0]["field"] == "kind"

    def test_duplicate_in_file_case_sensitive(self):
        # 'budi' vs 'Budi' BUKAN duplikat (case-sensitive) — beda baris valid.
        valid_idx, errors = self._run([{"username": "budi"}, {"username": "budi"}, {"username": "Budi"}])
        assert valid_idx == [0, 2]
        assert [e["reason_code"] for e in errors] == ["duplicate_in_file"]

    def test_whitespace_and_control_rows(self):
        _, errors = self._run([{"username": " budi"}, {"username": "bu\tdi"}])
        assert [e["reason_code"] for e in errors] == ["whitespace", "control_char"]

    def test_row_bounds(self):
        from domains.customers.services import CSV_MAX_ROWS, CSV_PREVIEW_ROWS

        assert CSV_MAX_ROWS == 5000
        assert CSV_PREVIEW_ROWS == 10


# ---------------------------------------------------------------------------
# ID grup konflik identitas — stabil & deterministik


def test_conflict_group_id_stable_and_order_insensitive():
    from domains.customers.services import conflict_group_id

    a = conflict_group_id(["budi.santoso", "Budi.Santoso"])
    b = conflict_group_id(["Budi.Santoso", "budi.santoso"])
    assert a == b
    assert len(a) == 16
    assert a != conflict_group_id(["budi.santoso"])


# ---------------------------------------------------------------------------
# Transisi state akun akses + kredensial (butuh PostgreSQL nyata)


@pytest.mark.django_db
class TestAccountStateAndCredentials:
    def _account(self, tenant_a):
        # Pemanggil wajib sudah dalam tenant_scope (satu level — scope
        # bersarang akan saling me-reset GUC app.tenant_id).
        from domains.customers.models import AccessAccount
        from domains.customers.services import provision_service_draft

        service = provision_service_draft(
            tenant_a, {"customer_name": "Budi", "username": "budi", "kind": "pppoe"}
        )
        return AccessAccount.objects.get(service=service)

    def test_suspend_then_activate(self, tenant_a):
        from domains.customers.services import set_account_state

        with tenant_scope(tenant_a.id):
            account = self._account(tenant_a)
            set_account_state(account, "suspended")
            assert account.state == "suspended"
            assert account.revision == 2
            set_account_state(account, "active")
            assert account.state == "active"
            assert account.revision == 3
            # idempoten: state sama tidak menaikkan revision
            set_account_state(account, "active")
            assert account.revision == 3

    def test_invalid_state_value_rejected(self, tenant_a):
        from domains.common.tenant_context import tenant_scope
        from domains.customers.services import set_account_state

        # Pemanggil wajib dalam tenant_scope (RLS aktif; pola fixture 2-a).
        with tenant_scope(tenant_a.id):
            account = self._account(tenant_a)
            with pytest.raises(ApiError) as exc:
                set_account_state(account, "disabled")
            assert exc.value.status_code == 422  # state di luar suspended/active → 422
            with pytest.raises(ApiError):
                set_account_state(account, "expired")

    def test_disabled_account_cannot_suspend_or_activate(self, tenant_a):
        from domains.common.tenant_context import tenant_scope
        from domains.customers.models import AccessAccount
        from domains.customers.services import set_account_state

        with tenant_scope(tenant_a.id):
            account = self._account(tenant_a)
            AccessAccount.objects.filter(id=account.id).update(state="disabled")
            account.refresh_from_db()
            # disabled/expired butuh izin/alur lebih kuat → 409 conflict.
            with pytest.raises(ApiError) as exc:
                set_account_state(account, "suspended")
            assert exc.value.status_code == 409
            with pytest.raises(ApiError):
                set_account_state(account, "active")

    def test_password_roundtrip_secret_ref_not_plaintext(self, tenant_a):
        from domains.common.crypto import SecretBox
        from domains.customers.services import reveal_password, set_password

        with tenant_scope(tenant_a.id):
            account = self._account(tenant_a)
            assert account.credential_state == "unknown"  # tanpa password → unknown (jujur)
            with pytest.raises(ApiError):
                reveal_password(account)  # belum ada kredensial → 409

            set_password(account, "s3cret-password")
            account.refresh_from_db()
            assert account.credential_state == "ready"
            assert account.revision == 2
            assert "s3cret-password" not in account.secret_ref  # tidak plaintext
            assert reveal_password(account) == "s3cret-password"
            assert SecretBox.decrypt_str(account.secret_ref) == "s3cret-password"
