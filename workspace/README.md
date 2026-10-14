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
    core/                 홈 대시보드, 메뉴 레지스트리, git 상태·자동 동기화·서버 코드 갱신
    ideas/                아이디어(허브). 상세 화면 안에 단계(Stage)·작업 로그(IdeaLog)
    tasks/                할 일. 아이디어·단계에 연결
    evidence/             증거 링크. 아이디어·단계에 연결
    memos/                메모
    docs/                 시장조사 md 문서 읽기 전용 뷰어
  templates/              base.html + 앱별 템플릿
  templates/includes/     icons.html(SVG 아이콘 모음), ic.html(아이콘 하나), field.html(폼 필드 한 칸)
  static/css/app.css      공통 디자인 시스템 (밝은 사이드바, 카드, 표, 배지, 토스트)
  static/js/app.js        토스트, git 상태 자동 갱신, 행 클릭, 복사, 단축키(/ 검색, Ctrl+Enter 저장)
  tools/gitsync.py        git add/commit/pull/push 를 하는 독립 스크립트
```

## 화면 구조 (아이디어 중심)

아이디어 하나가 허브다. 상세 화면 한 곳에서 다음을 다룬다.

- **진행 단계**: 순서대로 쌓는 세부 단계. 상태는 대기·진행·완료·보류, 진행은 한 번에 하나.
- **할 일**: 단계에 달린 다음 행동. 마감과 완료 체크.
- **증거 링크**: 조사 중 발견한 URL. 유형(의뢰 공고·리뷰·가격·정책·통계·경쟁 제품)과 한 줄 메모.
- **작업 로그**: 날짜순 짧은 기록. "오늘 한 일, 알게 된 것".
- **시장조사 개요**: 02·11 문서에서 옮긴 고객·불편·증거·판단 (접기).

홈은 진행 중인 아이디어(현재 단계·진행률·열린 할 일), 오늘·지난 할 일, 최근 로그를 보여 준다.

## 메뉴 추가 방법

1. `python manage.py startapp <이름> apps/<이름>` 으로 앱을 만들고 `config/settings.py` 의 `INSTALLED_APPS` 에 `apps.<이름>` 추가
2. `apps/<이름>/urls.py` 에 `app_name = "<이름>"` 지정, `config/urls.py` 에 include
3. `apps/core/menus.py` 의 `MENUS` 에 항목 추가 → 홈 카드와 좌측 메뉴에 자동 표시
4. 템플릿은 `templates/<이름>/` 에 두고 `{% extends "base.html" %}`

화면 뼈대는 `base.html` 의 block 으로 채운다: `heading`(제목), `subtitle`(제목 옆 설명), `actions`(오른쪽 버튼),
`toolbar`(제목 아래 필터 띠 `.filter-bar`), `content`(본문). 목록을 화면 가득 채우려면 `{% block body_class %}fill{% endblock %}`.
메뉴 `icon` 은 `templates/includes/icons.html` 의 symbol 이름이고, 화면에서는
`{% include "includes/ic.html" with name="plus" %}` 로 쓴다. 클래스는 `.btn primary|ghost|danger|sm`, `.card > .card-head + .card-body`,
`table.grid`, `.badge <톤>`, `.tag`, `.notice info|ok|warn|danger` 를 쓴다 (`static/css/app.css` 머리말 참고).

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
