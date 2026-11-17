"""Runner worker proses nyata untuk uji drain SIGTERM/SIGINT/SIGKILL (A08).

Pemakaian (dari direktori backend/):
    python -m tests.drain_worker --loop --interval 0.2 --drain-timeout 2

TEST_DATABASE_URL harus menunjuk database uji yang sudah termigrasi
(diteruskan oleh settings_test ke DATABASE_URL). Handler uji didaftarkan
sebelum command dijalankan.
"""
from __future__ import annotations

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "microtix.settings_test")

django.setup()

from django.core.management import call_command  # noqa: E402

from tests.drain_handlers import register_all  # noqa: E402

register_all()

if __name__ == "__main__":
    call_command("runworker", *sys.argv[1:])
