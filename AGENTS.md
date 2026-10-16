# AGENTS.md — 이 저장소에서 AI 에이전트가 지키는 규칙

이 저장소(`kwonjinbeom/jb_office`)는 사용자와 두 에이전트가 함께 쓴다.

- **Claude** (Claude Code, PC 로컬): 사용자와 화면을 보며 즉시 검증한다.
- **Codex** (Codex Cloud): GitHub 저장소를 클론해 작업하고 PR 로 제안한다.

둘 사이의 통신 채널은 git 이다. 이 문서가 공통 규칙의 단일 기준이며, 규칙을 바꿀 때는 이 파일을 고친다. (합의일: 2026-10-13)

> ## ⚠️ 가장 중요: 서버 반영·migrate 는 자동이다. 사용자에게 시키지 않는다. (2026-10-15 사용자 지시)
>
> - **`main` 에 push 되면 GitHub 웹훅이 서버를 스스로 갱신한다:** `git pull` → `pip install` → **`migrate`** → `collectstatic` → 재시작.
> - 그래서 **사용자는 '서버 코드 갱신' 버튼을 누를 일이 없고, 서버 콘솔에서 `migrate` 를 칠 일도 없다.**
> - 에이전트는 "서버 코드 갱신을 누르세요", "서버에서 migrate 하세요" 같은 안내·질문을 **절대 하지 않는다.** 사용자가 여러 번 지적했다.
> - 대신 push 뒤에 에이전트가 직접 반영 결과를 확인한다: `gh api repos/kwonjinbeom/jb_office/hooks/<id>/deliveries` 의 최근 응답이 `deployed <커밋>` 이면 migrate 까지 성공, `failed: ...` 면 실패다 (`apps/core/views.py` 웹훅, `apps/core/gitstate.py` `pull_and_reload`).
> - 실패했을 때만 원인과 함께 사용자에게 알린다.
>
> ## ⚠️ PR 병합도 묻지 않는다. 확인이 끝나면 바로 합친다. (2026-10-15 사용자 지시)
>
> - "합칠까요?" 하고 멈추지 않는다. 사용자 말: **"멈추지 말고 합치는 건 계속 합쳐. 다시 돌리면 되니까."**
> - PR 은 기록용이다. 올린 뒤 `manage.py check`·테스트·화면 확인이 끝났으면 에이전트가 바로 `gh pr merge` 하고, 위 방법으로 서버 반영(`deployed <커밋>`)까지 확인한 뒤 결과만 알린다.
> - 잘못 나갔으면 되돌리는 PR(revert)을 올려 다시 합친다.
> - 예외: 되돌릴 수 없게 서버 데이터를 지우는 migration(표·칸 삭제, 데이터 삭제)은 무엇이 지워지는지 사용자에게 먼저 말하고 합친다.

## 1. 브랜치와 반영 방식 (2026-10-13 개정)

**두 에이전트 모두 `main` 에 직접 커밋·푸시할 수 있다.** 사용자가 중간에서 전달하지 않아도 되게 하기 위해서다.
단, 아래 순서를 반드시 지킨다. Claude 와 Codex 에게 똑같이 적용된다.

1. 시작 전: `git pull --ff-only origin main` 으로 최신 상태를 받는다. 작업 트리가 clean 한지 확인한다.
2. 작업 중: 자기 작업과 관련된 파일만 바꾼다. 다른 에이전트가 방금 바꾼 파일을 되돌리지 않는다.
3. 끝낸 뒤: `workspace/` 를 바꿨다면 `manage.py check` 가 통과해야 한다. 화면을 바꿨다면 최소한 해당 URL 이 200 으로 뜨는지 확인한다.
4. 푸시 직전: 다시 `git pull --ff-only origin main` 을 한다. 갈라져 있으면 `git pull --no-rebase` 로 합치고 충돌을 해결한 뒤 푸시한다.
5. 금지: `push --force`, `reset --hard` 로 남의 커밋 제거, 상대 에이전트의 커밋을 되돌리는 revert (사용자 지시 없이).

PR 은 다음 경우에만 쓴다. 어느 경우든 **확인이 끝나면 에이전트가 바로 병합한다** (맨 위 둘째 상자 — 사용자에게 병합을 묻지 않는다).
- model 변경 등 migration 이 들어간 작업 → 무엇이 바뀌는지 기록을 남기려고 PR 로 올린다. PR 본문에 "병합하면 서버에 자동 migrate 됨" 과 지워지거나 바뀌는 데이터를 적는다.
- 구조를 크게 바꾸거나 상대 에이전트의 영역을 건드리는 작업 → PR 로 설명을 남기고 확인 뒤 병합한다. Codex PR 은 Claude 가 PC 에서 확인(check·테스트·화면)하고 병합한다.

브랜치 이름: Codex 는 `codex/<작업명>`, Claude 는 `claude/<작업명>` (PR 이 필요한 경우에만).

**서버 반영은 자동이다.** 누가 푸시했든 `main` 에 들어가면 웹훅으로 곧바로 서버에 반영되고 migrate 도 실행된다 (맨 위 상자).
그래서 main 에 push 하는 것 = 서비스에 내보내는 것이다. 덜 끝난 변경을 main 에 올리지 않는다.

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
- 에이전트는 어느 쪽도 서버 DB 파일을 직접 만지지 않는다. 데이터 구조를 바꿀 때는 migration 소스를 만든다. 서버 적용은 main push 때 웹훅이 자동으로 한다 — 사용자에게 콘솔에서 migrate 하라고 하지 않는다.
- Codex 는 임시 테스트 DB 와 읽기 전용 검사만 쓴다. `seed_ideas` 는 시험용 DB 에 예시 후보를 넣는 명령이며 서버 데이터의 원본이 아니다. '내 아이디어'에는 사용자가 일일 아이디어에서 직접 담은 것만 둔다 (2026-10-14: 기존 시드 후보를 모두 지움, `run.bat` 도 더는 시드를 넣지 않는다).

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
- **UI 원칙 (2026-10-16 사용자, 모든 화면):** ① 카드·칸은 **오와 열이 맞는다** — 같은 줄은 같은 크기·같은 격자, 내용 길이로 들쑥날쑥하지 않게 줄 수를 고정한다. ② 공통이 아닌 꾸밈 금지 — 중간에 갑자기 색 띠·색 박스·튀는 안내 문구를 넣지 않는다. ③ 글은 **짧게·요약해서**, 자세한 건 눌러서 본다. 사용자가 여러 번 요구한 원칙이다.
- 실행: `workspace\run.bat` (가상환경 생성 → 설치 → migrate → runserver).

## 6. 자동 동기화 (PC 전용)

- `.claude/settings.json` 의 Stop 훅과 서버 백그라운드 스레드가 `workspace/tools/gitsync.py` 를 실행해 `add -A → commit → pull --rebase → push` 한다.
- 이 동작은 PC 의 `main` 에서만 일어난다. Codex 환경에는 영향이 없다.

## 7. 커밋 메시지

- `feat:`, `fix:`, `docs:`, `chore:` 접두어를 쓴다. 자동 동기화 커밋은 `sync: <시각>` 이다.
- PR 본문에는 바꾼 이유, 확인 방법, 병합하면 서버에서 자동으로 일어나는 일(migrate 로 바뀌는 데이터 등)을 적는다.
