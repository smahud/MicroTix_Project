"""Settings khusus tes — bootstrap env deterministik SEBELUM settings utama.

pytest-django memanggil django.setup() pada pytest_load_initial_conftests,
SEBELUM conftest manapun dieksekusi. Setdefault env di conftest terbukti
terlambat: MT_SECRET_BOX_KEY terbeku kosong dan DATABASE_URL ambien
(mis. sqlite sandbox) menimpa target uji. Modul ini adalah titik masuk
paling awal yang dikendalikan repo (DJANGO_SETTINGS_MODULE pada pytest.ini).

Aturan: tes hanya berjalan pada PostgreSQL nyata (SQLite tidak dipakai);
TEST_DATABASE_URL selalu menang bila diset.
"""
import os

os.environ.setdefault("MT_ENV", "test")

_TEST_DB = os.environ.get("TEST_DATABASE_URL") or "postgresql://mtx_app@127.0.0.1:55432/microtix"
_ambient = os.environ.get("DATABASE_URL", "").split(":")[0]
if os.environ.get("TEST_DATABASE_URL") or _ambient not in ("postgres", "postgresql"):
    # DATABASE_URL ambien non-postgres (mis. sqlite sandbox) tidak dipakai untuk tes.
    os.environ["DATABASE_URL"] = _TEST_DB

os.environ.setdefault("MT_SECRET_KEY", "test-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("MT_SECRET_BOX_KEY", "test-secret-box-0123456789abcdef0123456789")
os.environ.setdefault("MT_STORAGE_ROOT", "/tmp/mtx-test-storage")

from .settings import *  # noqa: E402,F401,F403
