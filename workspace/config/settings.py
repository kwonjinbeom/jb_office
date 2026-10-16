"""
작업서버 Django settings.

두 가지 역할로 돌아간다. 역할은 환경변수 WORKSERVER_ROLE 로 정한다.
- dev    (기본): PC 로컬 개발. DEBUG 켜짐, 로그인 없음, git 자동 동기화 켜짐.
- server       : PythonAnywhere 같은 호스팅. DEBUG 꺼짐, 로그인 필수, 자동 동기화 꺼짐,
                 홈 화면에서 'git pull + 재시작' 버튼으로 코드를 갱신한다.

환경변수는 workspace/.env 파일(없으면 무시)에서도 읽는다. 예시는 .env.example 참고.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # workspace/
REPO_ROOT = BASE_DIR.parent  # git 저장소 루트 (jb_office/)

# tools/gitsync.py 를 어디서든 import 할 수 있게 한다.
TOOLS_DIR = BASE_DIR / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def _load_dotenv(path: Path) -> None:
    """KEY=VALUE 줄을 환경변수로 넣는다. 이미 있는 변수는 덮어쓰지 않는다. 외부 패키지 없이 처리."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---- ENV -------------------------------------------------------------------
ROLE = _env("WORKSERVER_ROLE", "dev").lower()  # dev | server
IS_SERVER = ROLE == "server"

SECRET_KEY = _env("DJANGO_SECRET_KEY", "local-workserver-not-secret")
DEBUG = _env_bool("DJANGO_DEBUG", not IS_SERVER)
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", ["*"])
CSRF_TRUSTED_ORIGINS = _env_list("DJANGO_CSRF_TRUSTED_ORIGINS", [])

# 로그인 요구 여부. 서버 역할이면 기본 켜짐, 로컬은 꺼짐.
REQUIRE_LOGIN = _env_bool("REQUIRE_LOGIN", IS_SERVER)

# DB 파일 위치. 서버에서는 저장소 밖(예: /home/<id>/data/db.sqlite3)에 두면 git pull 과 무관해진다.
DATABASE_PATH = Path(_env("DATABASE_PATH", str(BASE_DIR / "db.sqlite3")))

# git 자동 동기화 (apps/core/autosync.py). 서버에서는 push 하지 않으므로 기본 꺼짐.
AUTOSYNC = {
    "ENABLED": _env_bool("AUTOSYNC_ENABLED", not IS_SERVER),
    "INTERVAL_SECONDS": int(_env("AUTOSYNC_INTERVAL_SECONDS", "180")),
    "STATE_FILE": BASE_DIR / ".sync_state.json",
}

# 서버 역할: 홈의 '코드 갱신' 버튼이 git pull 뒤 이 파일을 touch 해서 앱을 재시작시킨다.
# PythonAnywhere 는 /var/www/<id>_pythonanywhere_com_wsgi.py 를 touch 하면 reload 된다.
DEPLOY = {
    "PULL_ENABLED": _env_bool("DEPLOY_PULL_ENABLED", IS_SERVER),
    "RELOAD_TOUCH_FILE": _env("DEPLOY_RELOAD_TOUCH_FILE", ""),
    # GitHub 웹훅(push) 수신용 비밀값. 비어 있으면 웹훅 엔드포인트는 거부한다.
    "WEBHOOK_SECRET": _env("DEPLOY_WEBHOOK_SECRET", ""),
    "WEBHOOK_BRANCH": _env("DEPLOY_WEBHOOK_BRANCH", "main"),
}
# 문서 보기 메뉴가 읽는 폴더 (저장소 기준 상대 경로). 읽기 전용.
DOCS_DIRS = [REPO_ROOT / "시장조사", REPO_ROOT]
# 날짜별 조사 후보 원본. 모델로 옮기기 전까지 저장소 파일로 보존한다.
DAILY_IDEAS_DIR = REPO_ROOT / "시장조사" / "일일아이디어"
# 논의 글(md). Claude·Codex 가 쓰고 push 하면 논의 현황·진행현황에 올라온다 (apps/discussions/docs.py)
DISCUSSIONS_DIR = REPO_ROOT / "논의"
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # 프로젝트 앱. 메뉴 하나 = 앱 하나.
    "apps.core",
    "apps.daily_ideas",
    "apps.ideas",
    "apps.evidence",
    "apps.tasks",
    "apps.memos",
    "apps.docs",
    "apps.content",
    "apps.discussions",
    "apps.writing",
    "apps.naver_writing",
    "apps.blog_types",
    "apps.site_templates",
    "apps.blog_rules",
    "apps.blog_ops",
    "apps.routines",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.trash_cleanup.TrashCleanupMiddleware",
]
if REQUIRE_LOGIN:
    # 모든 화면에 로그인을 요구한다. 로그인/로그아웃/관리자 로그인 화면은 Django 가 예외 처리한다.
    MIDDLEWARE.append("django.contrib.auth.middleware.LoginRequiredMiddleware")

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "login"

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
        "NAME": DATABASE_PATH,
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

TRASH_CLEANUP_ENABLED = _env_bool("TRASH_CLEANUP_ENABLED", True)

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

if IS_SERVER:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30일. 폰에서 매번 로그인하지 않게
