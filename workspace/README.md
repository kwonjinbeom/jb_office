# 작업서버

Django + SQLite 로 돌아가는 개인 작업용 로컬 솔루션 화면이다. 메뉴 하나가 앱 하나에 대응한다.

## 실행

```bat
workspace\run.bat
```

가상환경 생성, Django 설치, 마이그레이션, 일일루틴 링크(`jbroutine:`) 등록(`routine_link.bat`), `runserver` 까지 한 번에 한다.
브라우저에서 http://127.0.0.1:8000/ 을 연다.

수동으로 하려면:

```bat
cd workspace
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
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
    core/                 홈 대시보드, 메뉴 레지스트리, 휴지통, git 상태·자동 동기화·서버 반영 웹훅
    routines/             일일루틴 (실행·전체 실행·추가 실행, 커스텀 글쓰기, 프롬프트 관리). PC 터미널 claude 실행(local_run)
    writing/              글 (티스토리 쪽 편집기·원고 가져오기·붙여넣기 HTML 렌더)
    naver_writing/        글 (네이버 쪽 편집기·붙여넣기 HTML 렌더)
    blog_types/           글 관리(posts: 임시글 → 검토글 → 발행예정글 → 게시글 관리) · 카테고리 관리(글 분류 · 사이트 카테고리에 넣기)
    site_templates/       사이트별 템플릿(컨셉·규칙 보기) · 변환(요청문 · 변환 화면 · 붙여넣기 포맷)
    blog_rules/           사이트(Blog)와 사이트 체크 — 데이터는 여러 앱이 쓴다. 화면은 메뉴에서 뺐다
    blog_ops/             통계현황(사이트별 방문자·공감·댓글) · 모니터링(확인할 것 · 사이트별 파이프라인 · 발행 실적 · RSS 발행 확인 · 발행 완료 자동 처리)
    series/ · anime/ · anime_seasons/   memorily 티스토리 (블로그 자동화 연재 · 애니 총정리 · 분기별 애니 추천 및 후기)
    content/              블로그·카페 / 영상 콘텐츠 소재 목록
    daily_ideas/          일일 아이디어 (날짜별 JSON) · 검색 표준
    ideas/ · tasks/ · evidence/   내 아이디어와 그 단계·할 일·증거 링크
    studio/               창작콘텐츠 (인스타 카툰 · 숏폼 영상 · 쓰레드 글 · AI 이미지 설정집 · 검증 기록)
    schedule/             일정관리 (월 달력 · 매일 알림 · 반복)
    discussions/          진행현황 (논의/ 폴더의 md)
    memos/                메모
    docs/                 시장조사 md 문서 읽기 전용 뷰어
  templates/              base.html + 앱별 템플릿
  templates/includes/     icons.html(SVG 아이콘 모음), ic.html(아이콘 하나), field.html(폼 필드 한 칸)
  static/css/app.css      공통 디자인 시스템 (밝은 사이드바, 카드, 표, 배지, 토스트)
  static/js/app.js        토스트, git 상태 자동 갱신, 행 클릭, 복사, 단축키(/ 검색, Ctrl+Enter 저장)
  tools/gitsync.py        git add/commit/pull/push 를 하는 독립 스크립트
```

## 내 아이디어

아이디어 하나의 상세 화면 한 곳에서 다음을 다룬다.

- **진행 단계**: 순서대로 쌓는 세부 단계. 상태는 대기·진행·완료·보류, 진행은 한 번에 하나.
- **할 일**: 단계에 달린 다음 행동. 마감과 완료 체크.
- **증거 링크**: 조사 중 발견한 URL. 유형(의뢰 공고·리뷰·가격·정책·통계·경쟁 제품)과 한 줄 메모.
- **작업 로그**: 날짜순 짧은 기록. "오늘 한 일, 알게 된 것".
- **시장조사 개요**: 02·11 문서에서 옮긴 고객·불편·증거·판단 (접기).

홈은 진행 중인 아이디어(현재 단계·진행률·열린 할 일), 오늘·지난 할 일, 최근 로그를 보여 준다.

## 일일 아이디어

날짜마다 `시장조사/일일아이디어/<YYYY-MM-DD>.json` 하나. 화면 위쪽 달력에서 날짜를 옮긴다 (← → 키, 날짜 고르기).
목록에는 아이디어와 세부내용만 보이고, 항목을 누르면 구현 계획과 검토 근거가 펼쳐진다.
구현 계획은 항목의 `plan` (문장 목록 또는 `{title, detail}` 목록)을 쓰고, 없으면 만들 것·첫 검증·알릴 곳·돈 받는 방식으로 대신한다.
형식은 `apps/daily_ideas/data.py` 머리말. '내 아이디어'에는 여기서 직접 담은 것만 들어간다 (초기 시드는 넣지 않는다).
**조사 방법**(Claude·Codex 공통): `시장조사/00_아이디어_조사방법.md` — 트렌드는 참고만, 돈이 오가는 증거와 종합해 수익 경로가 서는 것만 아이디어로.

**아이디어 검색 표준** (`/daily-ideas/standard/`, 일일루틴 › 프롬프트 관리의 자료에서 연다): 조사할 때 Claude·Codex 에게 주는 조건을 항목별로 쓴다.
저장할 때마다 버전(v1, v2 …)이 DB 에 쌓인다. 조사를 맡길 때는 화면의 '요청문 복사'를 대화에 붙여 넣는다 — 에이전트는 서버 DB 를 직접 읽지 않는다.
조사 결과 JSON 의 `standard_version` 으로 어느 버전을 따랐는지 남기고, 일일 아이디어 화면에 표시된다. 항목 구성은 `apps/daily_ideas/standard.py`.

## 진행현황

대구분은 메뉴 이름(아이디어 · 블로그·카페 · 영상 콘텐츠), 중구분은 상위 주제. 메뉴마다 있던 '논의 현황'은 뺐다 (2026-10-23) — 진행현황 한곳에서 본다.
목록은 한 줄 제목만, 들어가면 정리한 글이 게시글처럼 보인다. 글은 저장소 `논의/<대구분>/` 의 md 로 쓰고 push 한다 (형식은 `논의/README.md`).

## 메뉴 추가 방법

1. `python manage.py startapp <이름> apps/<이름>` 으로 앱을 만들고 `config/settings.py` 의 `INSTALLED_APPS` 에 `apps.<이름>` 추가
2. `apps/<이름>/urls.py` 에 `app_name = "<이름>"` 지정, `config/urls.py` 에 include
3. `apps/core/menus.py` 의 `MENUS` 에 항목 추가 → 홈 카드와 좌측 메뉴에 자동 표시
   - 하위 메뉴는 그 항목의 `children=(Menu(...), ...)` 에 넣는다 → 좌측 메뉴에서 트리로 펼쳐진다 (예: 블로그·카페 › 글 관리 › 임시·검토글).
     하위 메뉴 화면의 뷰에서 `request.nav_key = "<key>"` 를 넣으면 그 항목이 강조된다.
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
