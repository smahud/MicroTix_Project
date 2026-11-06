"""Integrasi API documents (TK-109) — PostgreSQL nyata + RLS + trigger.

BIL-01/BIL-08, I18N-01 (snapshot bahasa/template; T23-I18-02), I18N-03.
Baris dibuat HANYA lewat services.issue_document dalam tenant_scope.
Fixture conftest: api_client/auth_client/owner/tenant_a/tenant_b.
"""
from __future__ import annotations

import hashlib
import stat
import time
from pathlib import Path

import pytest
from django.conf import settings
from django.db import connection
from django.db import DatabaseError, ProgrammingError

from domains.common.envelope import ApiError
from domains.common.tenant_context import tenant_scope
from domains.documents.models import IssuedDocument
from domains.documents.rendering import TEMPLATES, latest_template_version
from domains.documents.services import artifact_bytes, document_info, issue_document
from domains.identity.models import User
from domains.tenancy.models import Membership, Role

pytestmark = pytest.mark.integration

LIST_URL = "/api/v1/tenants/{tenant_id}/documents"


def invoice_values(doc_number: str) -> dict:
    """Snapshot nilai invoice uji — uang string, tanggal ISO (I18N-03)."""
    return {
        "tenant_name": "RT RW Net Melati",
        "doc_number": doc_number,
        "issued_date": "2026-11-01",
        "due_date": "2026-11-08",
        "customer_name": "Budi Santoso",
        "service_code": "SRV-0001",
        "lines": [{"description": "Paket 20M — periode November 2026", "amount": "150000.00"}],
        "total_amount": "150000.00",
    }


@pytest.fixture
def doc_paths():
    """Kumpulkan storage_path artifact; teardown hapus file (root privat bersama)."""
    paths: list[str] = []
    yield paths
    root = Path(settings.MT_STORAGE_ROOT)
    for path in paths:
        try:
            (root / path).unlink()
        except OSError:
            pass


def _issue_doc(
    tenant,
    doc_number: str,
    *,
    kind: str = "internet_invoice",
    ref_type: str = "billing_invoice",
    ref_id: str = "inv-1",
) -> IssuedDocument:
    """Terbitkan dokumen uji via service di dalam tenant_scope (RLS aktif)."""
    if kind == "receipt":
        values = {
            "tenant_name": "RT RW Net Melati",
            "doc_number": doc_number,
            "customer_name": "Budi Santoso",
            "received_at": "2026-11-06",
            "method": "cash",
            "applies_to": [{"invoice_number": "INV-x", "amount": "150000.00"}],
            "amount": "150000.00",
            "credit": "0",
        }
    else:
        values = invoice_values(doc_number)
    with tenant_scope(tenant.id):
        return issue_document(
            tenant_id=tenant.id,
            kind=kind,
            doc_number=doc_number,
            ref_type=ref_type,
            ref_id=ref_id,
            locale="id",
            values=values,
        )


# ---------------------------------------------------------------------------
# 1) Penerbitan: row + artifact privat 0600 + hash/size konsisten
# ---------------------------------------------------------------------------


def test_issue_document_writes_artifact_and_row(tenant_a, doc_paths):
    doc = _issue_doc(tenant_a, "INV-rtrw-aaaa000001-202611-0001")
    doc_paths.append(doc.storage_path)

    path = Path(settings.MT_STORAGE_ROOT) / doc.storage_path
    assert path.exists()
    assert path.parent.name == "documents"  # subdirektori privat, path opaque
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    data = path.read_bytes()
    assert data.startswith(b"%PDF-")
    assert hashlib.sha256(data).hexdigest() == doc.sha256
    assert path.stat().st_size == doc.size_bytes

    with tenant_scope(tenant_a.id):
        row = IssuedDocument.objects.get(id=doc.id)
        assert row.kind == "internet_invoice"
        assert row.locale == "id"
        assert row.template_version == "1"
        assert row.timezone == "Asia/Jakarta"
        assert row.values["customer_name"] == "Budi Santoso"
        assert row.sha256 == doc.sha256


# ---------------------------------------------------------------------------
# 2) Kekekalan row: trigger menolak UPDATE dan DELETE mentah
# ---------------------------------------------------------------------------


def test_raw_update_and_delete_blocked_by_trigger(tenant_a, doc_paths):
    doc = _issue_doc(tenant_a, "INV-rtrw-aaaa000001-202611-0002")
    doc_paths.append(doc.storage_path)

    # pytest.raises DI LUAR tenant_scope: exception menembus atomic → rollback
    # savepoint (transaksi PG sudah aborted oleh RAISE EXCEPTION trigger).
    with pytest.raises((DatabaseError, ProgrammingError)):
        with tenant_scope(tenant_a.id):
            with connection.cursor() as cur:
                cur.execute("UPDATE documents_issued_document SET doc_number = 'x'")
    with pytest.raises((DatabaseError, ProgrammingError)):
        with tenant_scope(tenant_a.id):
            with connection.cursor() as cur:
                cur.execute("DELETE FROM documents_issued_document")
    # Row tetap utuh — reprint tetap mungkin.
    with tenant_scope(tenant_a.id):
        assert IssuedDocument.objects.filter(id=doc.id).count() == 1


# ---------------------------------------------------------------------------
# 3) Duplikat nomor (tenant, kind, doc_number) → 409 conflict
# ---------------------------------------------------------------------------


def test_duplicate_doc_number_conflict(tenant_a, doc_paths):
    doc_number = "INV-rtrw-aaaa000001-202611-0003"
    with tenant_scope(tenant_a.id):
        first = issue_document(
            tenant_id=tenant_a.id,
            kind="internet_invoice",
            doc_number=doc_number,
            values=invoice_values(doc_number),
        )
    doc_paths.append(first.storage_path)

    # Duplikat (tenant, kind, doc_number) → 409 conflict; scope dalam di-rollback.
    with pytest.raises(ApiError) as exc:
        with tenant_scope(tenant_a.id):
            issue_document(
                tenant_id=tenant_a.id,
                kind="internet_invoice",
                doc_number=doc_number,
                values=invoice_values(doc_number),
            )
    assert exc.value.status_code == 409
    assert exc.value.code == "conflict"

    # Row pertama selamat; kind berbeda memakai nomor sama → boleh
    # (uniqueness per tenant+kind — nomor kwitansi beda namespace, BIL-01/08).
    with tenant_scope(tenant_a.id):
        assert IssuedDocument.objects.filter(kind="internet_invoice", doc_number=doc_number).count() == 1
        receipt = issue_document(
            tenant_id=tenant_a.id,
            kind="receipt",
            doc_number=doc_number,
            values={
                "tenant_name": "RT RW Net Melati",
                "doc_number": doc_number,
                "customer_name": "Budi Santoso",
                "received_at": "2026-11-06",
                "method": "cash",
                "applies_to": [{"invoice_number": "INV-x", "amount": "150000.00"}],
                "amount": "150000.00",
                "credit": "0",
            },
        )
    doc_paths.append(receipt.storage_path)


# ---------------------------------------------------------------------------
# 4) API daftar: filter eksak + paginasi kursor
# ---------------------------------------------------------------------------


def test_list_filter_and_pagination(auth_client, tenant_a, doc_paths):
    doc1 = _issue_doc(tenant_a, "INV-rtrw-aaaa000001-202611-0101", ref_id="inv-1")
    doc2 = _issue_doc(tenant_a, "INV-rtrw-aaaa000001-202611-0102", ref_id="inv-2")
    doc3 = _issue_doc(
        tenant_a,
        "KWI-rtrw-aaaa000001-202611-0103",
        kind="receipt",
        ref_type="billing_payment",
        ref_id="pay-1",
    )
    for doc in (doc1, doc2, doc3):
        doc_paths.append(doc.storage_path)

    base = LIST_URL.format(tenant_id=tenant_a.id)
    resp = auth_client.get(base)
    assert resp.status_code == 200
    page = resp.json()
    assert set(page.keys()) == {"items", "next_cursor"}
    numbers = {row["doc_number"] for row in page["items"]}
    assert doc1.doc_number in numbers and doc3.doc_number in numbers
    info = next(row for row in page["items"] if row["id"] == str(doc1.id))
    assert set(info.keys()) == {
        "id", "kind", "doc_number", "ref_type", "ref_id", "locale",
        "timezone", "template_version", "sha256", "size_bytes", "issued_at",
    }
    assert "storage_path" not in info  # path privat tidak diekspos

    # Filter eksak ref_type / ref_id / kind.
    payments = auth_client.get(f"{base}?ref_type=billing_payment").json()["items"]
    assert [row["doc_number"] for row in payments] == [doc3.doc_number]
    one = auth_client.get(f"{base}?ref_type=billing_invoice&ref_id=inv-2").json()["items"]
    assert [row["doc_number"] for row in one] == [doc2.doc_number]
    receipts = auth_client.get(f"{base}?kind=receipt").json()["items"]
    assert [row["doc_number"] for row in receipts] == [doc3.doc_number]

    # Paginasi: limit 2 → halaman 2 berisi sisanya (urutan issued_at desc).
    first_page = auth_client.get(f"{base}?limit=2").json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"]
    second_page = auth_client.get(f"{base}?limit=2&cursor={first_page['next_cursor']}").json()
    assert len(second_page["items"]) == 1
    assert second_page["next_cursor"] is None
    seen = [row["id"] for row in first_page["items"] + second_page["items"]]
    assert sorted(seen) == sorted(str(d.id) for d in (doc1, doc2, doc3))

    # limit tidak sah → 422 envelope.
    assert auth_client.get(f"{base}?limit=0").status_code == 422
    assert auth_client.get(f"{base}?cursor=rusak").status_code == 422


# ---------------------------------------------------------------------------
# 5) API artifact: PDF inline dengan nama file dokumen
# ---------------------------------------------------------------------------


def test_artifact_download(auth_client, tenant_a, doc_paths):
    doc = _issue_doc(tenant_a, "INV-rtrw-aaaa000001-202611-0104")
    doc_paths.append(doc.storage_path)

    resp = auth_client.get(f"/api/v1/tenants/{tenant_a.id}/documents/{doc.id}")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("application/pdf")
    assert resp.content.startswith(b"%PDF-")
    assert hashlib.sha256(resp.content).hexdigest() == doc.sha256  # reprint identik
    assert doc.doc_number in resp.headers["Content-Disposition"]
    assert "inline" in resp.headers["Content-Disposition"]

    # Id dokumen tidak dikenal / rusak → 404 generik.
    assert auth_client.get(f"/api/v1/tenants/{tenant_a.id}/documents/bukan-uuid").status_code == 404
    unknown = "00000000-0000-0000-0000-000000000000"
    assert auth_client.get(f"/api/v1/tenants/{tenant_a.id}/documents/{unknown}").status_code == 404


# ---------------------------------------------------------------------------
# 6) Isolasi lintas tenant: 404 generik + daftar kosong dari tenant B
# ---------------------------------------------------------------------------


def test_cross_tenant_isolation(auth_client, tenant_a, tenant_b, doc_paths):
    doc = _issue_doc(tenant_a, "INV-rtrw-aaaa000001-202611-0105")
    doc_paths.append(doc.storage_path)

    # Sesi kedua: owner tenant_b (pola fixture conftest tenant_b).
    owner_b = User.objects.create_user(
        email="owner-b2@test.local", full_name="Owner B2", password="test-password-1234567890", is_active=True
    )
    Membership.objects.create(user=owner_b, tenant=tenant_b, role=Role.OWNER)

    from rest_framework.test import APIClient

    client_b = APIClient(enforce_csrf_checks=False)
    client_b.force_login(owner_b)
    session = client_b.session
    session["active_tenant_id"] = str(tenant_b.id)
    session["auth_at"] = time.time()
    session.save()

    # Daftar milik B: tidak melihat dokumen A (RLS + konteks benar).
    page_b = client_b.get(LIST_URL.format(tenant_id=tenant_b.id)).json()
    assert page_b["items"] == []
    # Dokumen A dari konteks B → 404 generik (non-milik, jangan bocorkan).
    resp = client_b.get(f"/api/v1/tenants/{tenant_a.id}/documents/{doc.id}")
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
    # URL tenant B + id dokumen A → 404 juga (row B tidak ada).
    resp = client_b.get(f"/api/v1/tenants/{tenant_b.id}/documents/{doc.id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 7) Autentikasi: anonim 401; anggota tenant lain 404
# ---------------------------------------------------------------------------


def test_auth_gates(auth_client, tenant_a, tenant_b, doc_paths):
    doc = _issue_doc(tenant_a, "INV-rtrw-aaaa000001-202611-0106")
    doc_paths.append(doc.storage_path)

    # Klien anonim segar (fixture api_client bisa dipakai-pakai auth_client).
    from rest_framework.test import APIClient

    anon = APIClient(enforce_csrf_checks=False)
    assert anon.get(LIST_URL.format(tenant_id=tenant_a.id)).status_code == 401
    resp = anon.get(f"/api/v1/tenants/{tenant_a.id}/documents/{doc.id}")
    assert resp.status_code == 401
    # Login sebagai owner A, tapi URL tenant B (bukan anggota) → 404 generik.
    resp = auth_client.get(LIST_URL.format(tenant_id=tenant_b.id))
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


# ---------------------------------------------------------------------------
# 8) T23-I18-02: reprint memakai snapshot, bukan templat terbaru
# ---------------------------------------------------------------------------


def test_reprint_uses_issued_snapshot_not_new_template(tenant_a, doc_paths):
    with tenant_scope(tenant_a.id):
        doc = issue_document(
            tenant_id=tenant_a.id,
            kind="internet_invoice",
            doc_number="INV-rtrw-aaaa000001-202611-0107",
            values=invoice_values("INV-rtrw-aaaa000001-202611-0107"),
        )
        original = artifact_bytes(doc)
        sha_issued = doc.sha256
    doc_paths.append(doc.storage_path)

    # Daftarkan templat v2 BARU (mutasi lokal tes; dikembalikan setelahnya).
    TEMPLATES[("internet_invoice", "2")] = lambda values, locale: (
        "<html><body><p>TEMPLATE INTERNET_INVOICE V2</p></body></html>"
    )
    try:
        assert latest_template_version("internet_invoice") == "2"
        with tenant_scope(tenant_a.id):
            refetched = IssuedDocument.objects.get(id=doc.id)
            # Snapshot tetap versi "1": reprint TIDAK memakai templat terbaru.
            assert document_info(refetched)["template_version"] == "1"
            assert refetched.sha256 == sha_issued
            reprint = artifact_bytes(refetched)
            assert reprint == original
            assert reprint.startswith(b"%PDF-")
    finally:
        del TEMPLATES[("internet_invoice", "2")]
    assert latest_template_version("internet_invoice") == "1"


# ---------------------------------------------------------------------------
# 9) Integritas artifact: file dirusak → document_integrity 500
# ---------------------------------------------------------------------------


def test_artifact_integrity_error_on_tamper(tenant_a, doc_paths):
    with tenant_scope(tenant_a.id):
        doc = issue_document(
            tenant_id=tenant_a.id,
            kind="internet_invoice",
            doc_number="INV-rtrw-aaaa000001-202611-0108",
            values=invoice_values("INV-rtrw-aaaa000001-202611-0108"),
        )
        expected = artifact_bytes(doc)
    doc_paths.append(doc.storage_path)

    # Rusak artifact fisik; hash row tidak lagi cocok → ApiError integritas.
    (Path(settings.MT_STORAGE_ROOT) / doc.storage_path).write_bytes(b"junk")
    with pytest.raises(ApiError) as exc:
        artifact_bytes(doc)
    assert exc.value.status_code == 500
    assert exc.value.code == "document_integrity"

    # Pastikan pengujian tidak menyimpan byte asli di memori sebelum dirusak.
    assert expected.startswith(b"%PDF-")
