# jb_office Cloud 환경 설정 제안

이 문서는 Codex Cloud 설정 초안의 기준 버전 충돌(`stale_base`)로 자동 저장하지 못한 설정을 전달하기 위해 보존한다.

새 환경 setup 채팅에서는 현재 Cloud 설정 초안을 먼저 읽고, 기존 요구사항을 보존한 상태에서 아래 `install_script`와 `start_skill`을 반영한다. 저장소는 GitHub의 `kwonjinbeom/jb_office`, 기본 브랜치는 `main`을 사용한다.

## 환경변수

- `AUTOSYNC_ENABLED=0`
- `WORKSERVER_ROLE=dev`
- `DATABASE_PATH=/tmp/jb_office_cloud/db.sqlite3`

Cloud는 코드 개발·검증 역할만 수행한다. Git 자동 동기화를 비활성화하고, PythonAnywhere의 실제 DB와 완전히 분리된 `/tmp` 임시 DB만 사용한다.

## install_script

```bash
set -euo pipefail
cd /workspace/jb_office/workspace
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
mkdir -p /tmp/jb_office_cloud
export WORKSERVER_ROLE=dev
export AUTOSYNC_ENABLED=0
export DATABASE_PATH=/tmp/jb_office_cloud/db.sqlite3
export PYTHONDONTWRITEBYTECODE=1
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py seed_ideas
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate --check --plan
```

## start_skill

Use the existing checkout at `/workspace/jb_office`; do not create a Git worktree unless the user explicitly requests one.

Read `/workspace/jb_office/AGENTS.md` before making changes. As Codex Cloud, never commit or push directly to `main`; use a short `codex/<task>` branch and a pull request. Avoid editing files covered by active Claude work, and never run the repository's automatic Git synchronization in the Cloud checkout.

This is a Django 5.2 + SQLite application with separate `dev` and `server` roles. The source of truth is the PythonAnywhere database at `~/data/db.sqlite3`; it is not in Git. Never access or copy that production database in Codex Cloud. Cloud development must use only `/tmp/jb_office_cloud/db.sqlite3`, which may be migrated and seeded as disposable test data. Migration source files may be proposed in a PR, with a note that the user must apply them on PythonAnywhere.

Before starting, verify readiness:

```bash
cd /workspace/jb_office/workspace
mkdir -p /tmp/jb_office_cloud
export WORKSERVER_ROLE=dev
export AUTOSYNC_ENABLED=0
export DATABASE_PATH=/tmp/jb_office_cloud/db.sqlite3
export PYTHONDONTWRITEBYTECODE=1
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py seed_ideas
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate --check --plan
```

Start the development server in a persistent terminal session with automatic Git synchronization disabled:

```bash
cd /workspace/jb_office/workspace
WORKSERVER_ROLE=dev AUTOSYNC_ENABLED=0 DATABASE_PATH=/tmp/jb_office_cloud/db.sqlite3 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
```

Verify readiness locally (do not create a user-facing preview link for this loopback service):

```bash
curl -fsS http://127.0.0.1:8000/ >/dev/null
curl -fsS http://127.0.0.1:8000/ideas/ >/dev/null
curl -fsS http://127.0.0.1:8000/memos/ >/dev/null
```

Keep `WORKSERVER_ROLE=dev`, `AUTOSYNC_ENABLED=0`, and the `/tmp` database path for cloud development. Never configure PythonAnywhere server secrets or its production database path in Codex Cloud. The application's automatic sync and manual sync endpoints can stage, commit, pull, and push unrelated changes, so do not invoke them. Stage only task-specific files, review the diff, and use a pull request.

## 검증 기록

- Python 3.12.14, Django 5.2.18
- `manage.py check`: 통과
- `manage.py migrate --check --plan`: 미적용 마이그레이션 없음
- `pip check`: 의존성 충돌 없음
- 최신 `main` 커밋 `47a85a8`을 Cloud 체크아웃에서 검증
- dev 역할의 홈, 아이디어, 메모, 로그인, Git 상태 API, 정적 CSS: HTTP 200
- server 역할의 비로그인 차단, 로그인 화면, 로그인 후 홈 접근: 통과
- `/tmp` 임시 DB 마이그레이션과 초기 아이디어 35개 적재: 통과
- 저장소의 자체 테스트: 0건
