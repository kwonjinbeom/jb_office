# AGENTS.md — 이 저장소에서 AI 에이전트가 지키는 규칙

이 저장소(`kwonjinbeom/jb_office`)는 사용자와 두 에이전트가 함께 쓴다.

- **Claude** (Claude Code, PC 로컬): 사용자와 화면을 보며 즉시 검증한다.
- **Codex** (Codex Cloud): GitHub 저장소를 클론해 작업하고 PR 로 제안한다.

둘 사이의 통신 채널은 git 이다. 이 문서가 공통 규칙의 단일 기준이며, 규칙을 바꿀 때는 이 파일을 고친다. (합의일: 2026-10-13)

## 1. 브랜치와 반영 방식

| | Claude (PC) | Codex (Cloud) |
|---|---|---|
| 작업 브랜치 | `main` 직접 | 최신 `origin/main` 에서 `codex/<작업명>` |
| 반영 | 직접 push (자동 동기화 포함) | PR 로만 제안, `main` 직접 push 금지 |
| 병합 담당 | Claude 가 사용자 지시로 PR 을 받아 실행 검증 후 병합 | - |

Claude 가 `main` 에 직접 반영하기 전 확인 사항:

1. `git pull --ff-only origin main` 으로 최신 상태인지 확인한다.
2. 작업 트리가 clean 한지 확인한다. Stop 훅이 모든 변경을 자동 stage 하므로, 다른 미커밋 작업이 섞여 들어가면 안 된다.
3. 같은 파일을 건드리는 Codex PR 이 열려 있는지 확인한다. 있으면 먼저 병합하거나 사용자에게 알린다.

## 2. 담당 영역

| 영역 | Claude | Codex |
|---|---|---|
| `작업서버/` 코드 | 담당 | PR 로 제안 가능 |
| `작업서버/db.sqlite3` | 유일한 변경 주체 | 수정·교체·삭제·stage 금지 |
| Django migration 소스 | 작성·적용 | 작성 가능. PC DB 적용이 필요하면 PR 본문에 명시 |
| `시장조사/` 문서 | 수정 가능 | 수정 가능 |
| `코덱스 작업 폴더/` | 건드리지 않음 | 담당 |
| `AGENTS.md`, `README.md` | 합의 후 수정 | 합의 후 수정 |

## 3. DB 규칙 (중요)

- `작업서버/db.sqlite3` 는 바이너리라 git 이 병합하지 못한다. 충돌하면 한쪽 데이터가 사라진다.
- 그래서 **PC 의 Claude 만** 이 파일을 바꾼다. 폰·클라우드에서는 데이터를 고치지 않는다.
- Codex 는 추적 중인 DB 에 `migrate`, `seed_ideas` 를 실행하지 않는다. 임시 테스트 DB(예: `DJANGO_SETTINGS_MODULE` 을 바꾸거나 복사본 사용)와 읽기 전용 검사는 허용한다.
- 사용자가 PC 와 폰에서 번갈아 작업할 때는, 한쪽 작업을 push 한 뒤 다른 쪽을 시작한다.

## 4. 문서 규칙

- 같은 파일을 동시에 편집하지 않는다. git 자동 병합을 기대하지 말고, 시작 전에 pull 한다.
- 새 조사 문서는 `시장조사/NN_제목.md` 번호 규칙을 따른다.

## 5. 작업서버 구조 요약

자세한 내용은 `작업서버/README.md`.

- Django 5.2 + SQLite. 메뉴 하나 = 앱 하나 (`apps/<이름>/`).
- 새 메뉴 추가: 앱 생성 → `config/settings.py` INSTALLED_APPS → `config/urls.py` include → `apps/core/menus.py` MENUS 에 항목 추가. 홈 카드와 좌측 메뉴가 자동으로 생긴다.
- 템플릿은 `templates/<앱>/` 에 두고 `{% extends "base.html" %}`. 스타일은 `static/css/app.css` 하나, 외부 CSS 프레임워크 없음, 사무적이고 깔끔한 톤 유지.
- 실행: `작업서버\run.bat` (가상환경 생성 → 설치 → migrate → seed → runserver).

## 6. 자동 동기화 (PC 전용)

- `.claude/settings.json` 의 Stop 훅과 서버 백그라운드 스레드가 `작업서버/tools/gitsync.py` 를 실행해 `add -A → commit → pull --rebase → push` 한다.
- 이 동작은 PC 의 `main` 에서만 일어난다. Codex 환경에는 영향이 없다.

## 7. 커밋 메시지

- `feat:`, `fix:`, `docs:`, `chore:` 접두어를 쓴다. 자동 동기화 커밋은 `sync: <시각>` 이다.
- PR 본문에는 바꾼 이유, 확인 방법, PC 에서 추가로 해야 할 일(migrate 등)을 적는다.
