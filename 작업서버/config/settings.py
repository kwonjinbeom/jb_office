"""
작업서버 Django settings.

로컬 전용 도구다. 외부에 공개하지 않는다는 전제로 DEBUG=True, 인증 없음으로 운영한다.
환경변수로 바꿀 수 있는 값은 아래 ENV 블록에 모아 둔다.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # 작업서버/
REPO_ROOT = BASE_DIR.parent  # git 저장소 루트 (sub_pj/)

# tools/gitsync.py 를 어디서든 import 할 수 있게 한다.
TOOLS_DIR = BASE_DIR / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ---- ENV -------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-workserver-not-secret")
DEBUG = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = ["*"]

# git 자동 동기화 (apps/core/autosync.py)
AUTOSYNC = {
    "ENABLED": _env_bool("AUTOSYNC_ENABLED", True),
    "INTERVAL_SECONDS": int(os.environ.get("AUTOSYNC_INTERVAL_SECONDS", "180")),
    "STATE_FILE": BASE_DIR / ".sync_state.json",
}
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 프로젝트 앱. 메뉴 하나 = 앱 하나.
    "apps.core",
    "apps.ideas",
    "apps.memos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.navigation",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
