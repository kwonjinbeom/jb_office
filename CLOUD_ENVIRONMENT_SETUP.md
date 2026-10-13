# jb_office Cloud 환경 설정 제안

이 문서는 Codex Cloud 설정 초안의 기준 버전 충돌(`stale_base`)로 자동 저장하지 못한 설정을 전달하기 위해 보존한다.

새 환경 setup 채팅에서는 현재 Cloud 설정 초안을 먼저 읽고, 기존 요구사항을 보존한 상태에서 아래 `install_script`와 `start_skill`을 반영한다. 저장소는 GitHub의 `kwonjinbeom/jb_office`, 기본 브랜치는 `main`을 사용한다.

## 환경변수

- `AUTOSYNC_ENABLED=0`

Git 자동 동기화가 다른 AI의 변경까지 stage·commit·pull·push하지 않도록 반드시 비활성화한다.

## install_script

```bash
set -euo pipefail
cd /workspace/jb_office/작업서버
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
AUTOSYNC_ENABLED=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py check
AUTOSYNC_ENABLED=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py migrate --check --plan
```

## start_skill

Use the existing checkout at `/workspace/jb_office`; do not create a Git worktree unless the user explicitly requests one.

Read `/workspace/jb_office/AGENTS.md` before making changes. As Codex Cloud, never commit or push directly to `main`; use a short `codex/<task>` branch and a pull request. Avoid editing files covered by active Claude work, and never run the repository's automatic Git synchronization in the Cloud checkout.

This is a local-only Django 5.2 + SQLite application. The tracked database contains user data and is owned by the PC workflow. Never modify, replace, delete, or stage `/workspace/jb_office/작업서버/db.sqlite3` in Codex Cloud. Do not run `migrate` or seed commands against it. Read-only migration checks are allowed, and write tests must use a temporary test database. Migration source files may be proposed in a PR, with a note that the PC workflow must apply them.

Before starting, verify readiness:

```bash
cd /workspace/jb_office/작업서버
AUTOSYNC_ENABLED=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py check
AUTOSYNC_ENABLED=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py migrate --check --plan
```

Start the development server in a persistent terminal session with automatic Git synchronization disabled:

```bash
cd /workspace/jb_office/작업서버
AUTOSYNC_ENABLED=0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
```

Verify readiness locally (do not create a user-facing preview link for this loopback service):

```bash
curl -fsS http://127.0.0.1:8000/ >/dev/null
curl -fsS http://127.0.0.1:8000/ideas/ >/dev/null
curl -fsS http://127.0.0.1:8000/memos/ >/dev/null
```

Keep `AUTOSYNC_ENABLED=0` for cloud development: the application's default autosync and manual sync endpoints can stage, commit, pull, and push unrelated changes. Stage only task-specific files, review the diff, and use a pull request.

## 검증 기록

- Python 3.12.14, Django 5.2.18
- `manage.py check`: 통과
- `manage.py migrate --check --plan`: 미적용 마이그레이션 없음
- `pip check`: 의존성 충돌 없음
- 홈, 아이디어, 메모, Git 상태 API, 정적 CSS: HTTP 200
- 임시 테스트 DB의 아이디어·메모 CRUD: 통과
- 저장소의 자체 테스트: 0건
