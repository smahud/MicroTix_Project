"""Pengaturan Django MicroTix — lingkungan dikendalikan variabel environment.

Kontrak: docs/ARCHITECTURE.md (stack §1, sesi/cookie §2/§3, data §4).
Produksi memakai env nyata; dev memakai .env lokal; tes memakai pengaturan uji.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from .dburl import parse_db_url

BASE_DIR = Path(__file__).resolve().parent.parent

ENV = os.environ.get("MT_ENV", "dev")  # dev | test | production
DEBUG = ENV == "dev"
SECRET_KEY = os.environ.get("MT_SECRET_KEY", "")
if not SECRET_KEY:
    if ENV == "production":
        raise RuntimeError("MT_SECRET_KEY wajib diisi pada production")
    # Dev/test: kunci ephemeral — sesi dev tidak dipertahankan antar restart.
    SECRET_KEY = secrets.token_urlsafe(64)

# Kunci enkripsi rahasia tingkat aplikasi (AEAD) — key di luar DB (ARCHITECTURE §7).
MT_SECRET_BOX_KEY = os.environ.get("MT_SECRET_BOX_KEY", "")
if MT_SECRET_BOX_KEY and len(MT_SECRET_BOX_KEY) < 32:
    raise RuntimeError("MT_SECRET_BOX_KEY minimal 32 karakter")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    # Domain modular monolith — urutan tidak berpengaruh fungsional.
    "domains.tenancy",
    "domains.identity",
    "domains.jobs",
    "domains.audit",
    "domains.subscriptions",
    "domains.network",
    "domains.customers",
    "domains.radius",
    "domains.backups",
    "domains.monitoring",
    "domains.config",
    "domains.i18n",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "domains.common.middleware.RequestIdLocaleMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "microtix.urls"
WSGI_APPLICATION = "microtix.wsgi.application"
ASGI_APPLICATION = "microtix.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database (PostgreSQL 17 nyata; SQLite tidak dipakai) ---
_db_url = os.environ.get("DATABASE_URL", "postgresql://mtx_app@127.0.0.1:55432/microtix")
DATABASES = {"default": parse_db_url(_db_url).as_django()}
# Migrasi berjalan sebagai peran terpisah (ARCHITECTURE §4: migrator terpisah).
MIGRATE_DATABASE_URL = os.environ.get(
    "MIGRATE_DATABASE_URL", "postgresql://mtx_migrator@127.0.0.1:55432/microtix"
)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "identity.User"

# --- Password hashing: Argon2id (ARCHITECTURE §3) ---
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # kompatibilitas data lama saja
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Sesi: cookie HttpOnly/Secure/SameSite=Lax + CSRF (ARCHITECTURE §2) ---
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME = "mtx_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = ENV == "production"
SESSION_COOKIE_AGE = 8 * 60 * 60  # idle; kebijakan absolut di tengah sesi (identity)
CSRF_COOKIE_NAME = "mtx_csrf"
CSRF_COOKIE_HTTPONLY = False  # SPA membaca cookie untuk header x-csrf-token
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = ENV == "production"
CSRF_HEADER_NAME = "HTTP_X_CSRF_TOKEN"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = ENV == "production"
SECURE_HSTS_SECONDS = 31536000 if ENV == "production" else 0

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "domains.identity.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "domains.common.envelope.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "MicroTix API",
    "DESCRIPTION": "API platform manajemen ISP MicroTix (kontrak: docs/ARCHITECTURE.md §5).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# --- Path konfigurasi dan penyimpanan ---
REPO_ROOT = BASE_DIR.parent
MT_DOCS_DIR = Path(os.environ.get("MT_DOCS_DIR", REPO_ROOT / "docs"))
MT_STORAGE_ROOT = Path(os.environ.get("MT_STORAGE_ROOT", BASE_DIR / ".storage"))
MT_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

# --- Mail: dev memakai console (Mailpit SMTP saat tersedia) ---
if ENV == "dev":
    EMAIL_BACKEND = os.environ.get("MT_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
else:
    EMAIL_BACKEND = os.environ.get("MT_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
    EMAIL_HOST = os.environ.get("MT_EMAIL_HOST", "127.0.0.1")
    EMAIL_PORT = int(os.environ.get("MT_EMAIL_PORT", "1025"))

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = Path(os.environ.get("MT_STATIC_ROOT", BASE_DIR / ".static"))

ALLOWED_HOSTS = [h for h in os.environ.get("MT_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

# --- Keamanan skema upload/tandatangan (TK-106) ---
MT_UPLOAD_SIGNING_KEY = os.environ.get("MT_UPLOAD_SIGNING_KEY", SECRET_KEY)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("MT_LOG_LEVEL", "INFO")},
    "loggers": {
        # Jangan pernah log isi rahasia.
        "django.request": {"level": "WARNING"},
    },
}
