"""Tes unit PA-006 — normalisasi hash body v2 (REV-1311-03).

Field identitas UUID yang dideklarasikan call site (`body_uuid_fields`)
dinormalkan ke bentuk canonical sebelum HMAC:
- ejaan alias UUID (huruf besar/urn/kurung/tanpa hyphen) → hash sama;
- string opaque/semantik (username, kode, pesan) exact-case TIDAK diubah;
- list dinormalkan per elemen; urutan = semantik (tidak diurutkan);
- nilai bukan UUID dipertahankan apa adanya (validasi tetap milik domain).

Dideklarasikan saat ini: service_billing_package(package_id),
service_provision(router_id), migration_commit(selected_account_ids).
"""
from __future__ import annotations

import uuid as _uuid

import pytest

from domains.common.idempotency import _body_hash, _body_hash_legacy

pytestmark = pytest.mark.unit


def test_package_id_alias_shapes_share_hash():
    package = _uuid.uuid4()
    shapes = [
        str(package),
        str(package).upper(),
        package.hex,
        package.hex.upper(),
        f"urn:uuid:{package}",
        f"{{{package}}}",
    ]
    hashes = {_body_hash({"package_id": s}, ("package_id",)) for s in shapes}
    assert len(hashes) == 1, "semua ejaan alias UUID harus menghasilkan hash canonical sama"


def test_router_id_and_selected_account_ids_normalized():
    router = _uuid.uuid4()
    assert _body_hash({"router_id": router.hex.upper()}, ("router_id",)) == _body_hash(
        {"router_id": str(router)}, ("router_id",)
    )
    a, b = _uuid.uuid4(), _uuid.uuid4()
    left = _body_hash({"selected_account_ids": [str(a).upper(), str(b).upper()]}, ("selected_account_ids",))
    right = _body_hash({"selected_account_ids": [str(a), str(b)]}, ("selected_account_ids",))
    assert left == right


def test_list_order_is_semantic_not_sorted():
    a, b = _uuid.uuid4(), _uuid.uuid4()
    forward = _body_hash({"selected_account_ids": [str(a), str(b)]}, ("selected_account_ids",))
    backward = _body_hash({"selected_account_ids": [str(b), str(a)]}, ("selected_account_ids",))
    assert forward != backward, "urutan array adalah semantik dan tidak boleh diurutkan"


def test_opaque_strings_exact_case_preserved():
    # Username/kode/pesan TIDAK diubah — hanya field yang dideklarasikan.
    body_a = {"username": "Andi", "note": "Pembayaran-", "code": "Xy-12"}
    body_b = {"username": "andi", "note": "Pembayaran-", "code": "Xy-12"}
    body_c = {"username": "Andi", "note": "Pembayaran+", "code": "Xy-12"}
    assert _body_hash(body_a) != _body_hash(body_b)  # case username = identitas beda
    assert _body_hash(body_a) != _body_hash(body_c)
    # Tanpa field dideklarasikan, v2 identik dengan v1 raw (kompatibilitas).
    assert _body_hash(body_a) == _body_hash_legacy(body_a)


def test_non_uuid_values_kept_verbatim():
    weird = {"package_id": "not-a-uuid", "router_id": 12345, "n": None}
    assert _body_hash(weird, ("package_id", "router_id")) == _body_hash_legacy(weird)


def test_nested_and_non_dict_bodies_untouched():
    payload = [{"a": 1}, {"b": "x"}]
    assert _body_hash(payload, ("package_id",)) == _body_hash_legacy(payload)
    assert _body_hash("string-body") == _body_hash_legacy("string-body")
    assert _body_hash(None) == _body_hash_legacy(None)
