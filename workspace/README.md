# 작업서버

Django + SQLite 로 돌아가는 개인 작업용 로컬 솔루션 화면이다. 메뉴 하나가 앱 하나에 대응한다.

## 실행

```bat
workspace\run.bat
```

가상환경 생성, Django 설치, 마이그레이션, 초기 데이터 적재, `runserver` 까지 한 번에 한다.
브라우저에서 http://127.0.0.1:8000/ 을 연다.

수동으로 하려면:

```bat
cd workspace
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_ideas
.venv\Scripts\python manage.py runserver
```

## 구조

```
workspace/
  manage.py
  run.bat                 실행 스크립트
  requirements.txt
  db.sqlite3              로컬 개발용 임시 DB (git 제외). 실제 데이터는 서버에 있다 → DEPLOY.md
  .env                    역할·비밀 설정 (git 제외). 예시는 .env.example
  DEPLOY.md               PythonAnywhere 배포 안내
  deploy/                 서버용 WSGI 파일 템플릿
  config/                 settings, urls
  apps/
    core/                 홈, 메뉴 레지스트리, git 상태·자동 동기화
    ideas/                아이디어 리스트 (시장조사 후보 C01~C35)
    memos/                메모
  templates/              base.html + 앱별 템플릿
  static/css/app.css      공통 스타일 (사무용 톤)
  static/js/app.js        git 배지 자동 갱신
  tools/gitsync.py        git add/commit/pull/push 를 하는 독립 스크립트
```

## 메뉴 추가 방법

1. `python manage.py startapp <이름> apps/<이름>` 으로 앱을 만들고 `config/settings.py` 의 `INSTALLED_APPS` 에 `apps.<이름>` 추가
2. `apps/<이름>/urls.py` 에 `app_name = "<이름>"` 지정, `config/urls.py` 에 include
3. `apps/core/menus.py` 의 `MENUS` 에 항목 추가 → 홈 카드와 좌측 메뉴에 자동 표시
4. 템플릿은 `templates/<이름>/` 에 두고 `{% extends "base.html" %}`

## git 자동 동기화

세 경로가 같은 `tools/gitsync.py` 를 쓴다.

| 경로 | 시점 | 설정 |
|---|---|---|
| Claude Code Stop 훅 | Claude 가 한 턴을 끝낼 때마다 | `.claude/settings.json` |
| 서버 백그라운드 스레드 | `runserver` 중 180초마다 변경이 있을 때 | `AUTOSYNC_ENABLED`, `AUTOSYNC_INTERVAL_SECONDS` 환경변수 |
| 홈 화면 "지금 동기화" 버튼 / `manage.py gitsync` | 수동 | - |

동작: `git add -A` → 변경 있으면 커밋 → `pull --rebase --autostash` → `push`.
결과는 `workspace/.sync_state.json` (git 제외) 에 남고 홈 화면에 표시된다.

## 역할 (WORKSERVER_ROLE)

| | dev (기본, PC) | server (PythonAnywhere) |
|---|---|---|
| DEBUG | 켜짐 | 꺼짐 |
| 로그인 | 없음 | 필수 (`createsuperuser` 계정) |
| 자동 동기화 | 켜짐 | 꺼짐 |
| 홈 버튼 | 지금 동기화 (commit+push) | 서버 코드 갱신 (pull+reload) |
| DB | 로컬 임시 | `DATABASE_PATH` (저장소 밖) |

데이터의 원본은 서버 DB 하나다. PC 에서 실제 데이터를 고칠 때도 브라우저로 서버에 접속한다.
로컬 `runserver` 는 코드 개발·검증용이다.
