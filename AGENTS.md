# AGENTS.md — 이 저장소에서 AI 에이전트가 지키는 규칙

이 저장소(`kwonjinbeom/jb_office`)는 사용자와 두 에이전트가 함께 쓴다.

- **Claude** (Claude Code, PC 로컬): 사용자와 화면을 보며 즉시 검증한다.
- **Codex** (Codex Cloud): GitHub 저장소를 클론해 작업하고 PR 로 제안한다.

둘 사이의 통신 채널은 git 이다. 이 문서가 공통 규칙의 단일 기준이며, 규칙을 바꿀 때는 이 파일을 고친다. (합의일: 2026-10-13)

## 1. 브랜치와 반영 방식 (2026-10-13 개정)

**두 에이전트 모두 `main` 에 직접 커밋·푸시할 수 있다.** 사용자가 중간에서 전달하지 않아도 되게 하기 위해서다.
단, 아래 순서를 반드시 지킨다. Claude 와 Codex 에게 똑같이 적용된다.

1. 시작 전: `git pull --ff-only origin main` 으로 최신 상태를 받는다. 작업 트리가 clean 한지 확인한다.
2. 작업 중: 자기 작업과 관련된 파일만 바꾼다. 다른 에이전트가 방금 바꾼 파일을 되돌리지 않는다.
3. 끝낸 뒤: `workspace/` 를 바꿨다면 `manage.py check` 가 통과해야 한다. 화면을 바꿨다면 최소한 해당 URL 이 200 으로 뜨는지 확인한다.
4. 푸시 직전: 다시 `git pull --ff-only origin main` 을 한다. 갈라져 있으면 `git pull --no-rebase` 로 합치고 충돌을 해결한 뒤 푸시한다.
5. 금지: `push --force`, `reset --hard` 로 남의 커밋 제거, 상대 에이전트의 커밋을 되돌리는 revert (사용자 지시 없이).

PR 은 다음 경우에만 쓴다.
- model 변경 등 서버에서 `migrate` 가 필요한 작업 → PR 본문에 "서버 migrate 필요" 를 적는다.
- 구조를 크게 바꾸거나 상대 에이전트의 영역을 건드리는 작업 → PR 로 설명을 남기고, 사용자가 병합을 지시한다.

브랜치 이름: Codex 는 `codex/<작업명>`, Claude 는 `claude/<작업명>` (PR 이 필요한 경우에만).

**서버 반영은 사용자가 한다.** 누가 푸시했든 PythonAnywhere 홈 화면의 '서버 코드 갱신' 버튼을 사용자가 누를 때 반영된다.
그래서 main 에 들어간 코드가 곧바로 서비스에 나가지는 않는다.

## 2. 담당 영역

| 영역 | Claude | Codex |
|---|---|---|
| `workspace/` 코드 | 작업 가능 | 작업 가능 |
| `workspace/db.sqlite3` | 유일한 변경 주체 | 수정·교체·삭제·stage 금지 |
| Django migration 소스 | 작성·적용 | 작성 가능. PC DB 적용이 필요하면 PR 본문에 명시 |
| `시장조사/` 문서 | 수정 가능 | 수정 가능 |
| `코덱스 작업 폴더/` | 건드리지 않음 | 담당 |
| `AGENTS.md`, `README.md` | 합의 후 수정 | 합의 후 수정 |

## 3. DB 규칙 (중요)

- **실제 데이터는 PythonAnywhere 서버의 `~/data/db.sqlite3` 하나다.** git 에는 DB 파일이 없다 (`.gitignore`). 배포 방법은 `workspace/DEPLOY.md`.
- PC 와 폰은 브라우저로 서버(`https://<아이디>.pythonanywhere.com`)에 접속해 데이터를 고친다. 로컬 `workspace/db.sqlite3` 는 개발용 임시 DB 일 뿐이다.
- 에이전트는 어느 쪽도 서버 DB 파일을 직접 만지지 않는다. 데이터 구조를 바꿀 때는 migration 소스를 만들고, 서버에서 `migrate` 가 필요하다고 PR 또는 커밋 메시지에 명시한다. 서버 적용은 사용자가 Bash 콘솔에서 한다.
- Codex 는 임시 테스트 DB 와 읽기 전용 검사만 쓴다. `seed_ideas` 는 새 DB 를 만들 때만 쓰는 초기 데이터이며, 서버 데이터의 원본이 아니다.

## 4. 문서 규칙

- 같은 파일을 동시에 편집하지 않는다. git 자동 병합을 기대하지 말고, 시작 전에 pull 한다.
- 새 조사 문서는 `시장조사/NN_제목.md` 번호 규칙을 따른다.

## 5. 작업서버 구조 요약

자세한 내용은 `workspace/README.md`.

- Django 5.2 + SQLite. 메뉴 하나 = 앱 하나 (`apps/<이름>/`).
- **아이디어(`apps/ideas`)가 허브다.** 단계(Stage)·작업 로그(IdeaLog)는 ideas 앱 안에, 할 일(tasks)·증거(evidence)는 아이디어·단계에 FK 로 연결된다. 새 기능은 가능하면 아이디어 상세 화면 안으로 들어가야 한다. 범용 도구(장부, CRM, 통계)는 사용자가 요청하기 전에는 만들지 않는다.
- Python 의존성을 추가하면 `requirements.txt` 에 넣고, 커밋 메시지에 "서버 pip install 필요" 를 적는다 (현재 Markdown 패키지가 그렇다).
- 새 메뉴 추가: 앱 생성 → `config/settings.py` INSTALLED_APPS → `config/urls.py` include → `apps/core/menus.py` MENUS 에 항목 추가. 홈 카드와 좌측 메뉴가 자동으로 생긴다.
- 템플릿은 `templates/<앱>/` 에 두고 `{% extends "base.html" %}`. 스타일은 `static/css/app.css` 하나, 외부 CSS 프레임워크 없음, 사무적이고 깔끔한 톤 유지.
- 실행: `workspace\run.bat` (가상환경 생성 → 설치 → migrate → seed → runserver).

## 6. 자동 동기화 (PC 전용)

- `.claude/settings.json` 의 Stop 훅과 서버 백그라운드 스레드가 `workspace/tools/gitsync.py` 를 실행해 `add -A → commit → pull --rebase → push` 한다.
- 이 동작은 PC 의 `main` 에서만 일어난다. Codex 환경에는 영향이 없다.

## 7. 커밋 메시지

- `feat:`, `fix:`, `docs:`, `chore:` 접두어를 쓴다. 자동 동기화 커밋은 `sync: <시각>` 이다.
- PR 본문에는 바꾼 이유, 확인 방법, PC 에서 추가로 해야 할 일(migrate 등)을 적는다.
