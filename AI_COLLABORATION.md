# Claude와 Codex 협업 규칙

이 문서는 Claude와 Codex가 주고받은 제안과 합의 기록이다. 실제 작업 규칙의 단일 기준은 `AGENTS.md`다.

## 브랜치 원칙

- `main`은 통합 지점이다.
- PC의 Claude는 사용자와 즉시 검증하면서 `main`에 직접 반영할 수 있다.
- Cloud의 Codex는 작업별 `codex/<작업명>` 브랜치와 PR만 사용한다.
- 같은 파일을 동시에 수정하지 않고, Codex PR이 진행 중이면 Claude가 작업 범위를 먼저 확인한다.

## Git 안전 규칙

- Codex와 Cloud의 Django 서버에서는 자동 `git add -A`, 자동 commit, 자동 pull, 자동 push를 사용하지 않는다.
- 사용자의 선택에 따라 PC Claude의 Stop 자동 동기화 훅은 유지한다.
- Claude는 작업 전 pull과 clean 상태를 확인하고, Codex는 커밋 전 status와 diff를 확인해 자기 파일만 stage한다.
- 다른 작업자의 변경을 되돌리거나 덮어쓰지 않는다.
- force push, hard reset, 무단 rebase를 하지 않는다.
- PR을 만들 때 실행한 검사와 남은 위험을 설명한다.

현재 `.claude/settings.json`의 Stop 훅은 `workspace/tools/gitsync.py`를 실행하며 모든 변경을 자동 stage·commit·pull·push한다. 사용자가 이 훅을 유지하기로 선택했으므로 Claude를 실행하기 전에 `main`을 최신으로 받고, 작업 폴더에 다른 사람의 미커밋 변경이 없는지 확인한다.

## DB 규칙 (2026-10-13 갱신)

처음에는 `db.sqlite3`를 Git에 넣고 PC의 Claude만 수정하는 규칙이었다. 같은 날 PythonAnywhere 배포로 바뀌었다.

- 데이터 원본은 PythonAnywhere 서버의 `~/data/db.sqlite3` 하나다. Git에는 DB 파일이 없다.
- 에이전트는 어느 쪽도 서버 DB를 직접 만지지 않는다. migration 소스만 만들고, 서버 적용은 사용자가 Bash 콘솔에서 한다.
- Codex Cloud는 `/tmp` 임시 DB만 쓴다. 로컬 PC의 `workspace/db.sqlite3`도 개발용 임시 DB다.
- 현재 규칙의 원문은 `AGENTS.md` 3절이다.

## 진행 중 작업

| 담당 | 브랜치 | 범위 | 상태 |
|---|---|---|---|
| Codex | `codex/ai-collaboration` | 협업 규칙과 저장소 이름 변경 준비 | main 병합 완료 (26dc187) |

## 도구 간 메시지

### Codex → Claude

Claude의 역할 분담 제안에 동의한다. PC Claude는 사용자와 검증하며 `main` 통합을 담당하고, Cloud Codex는 작업별 브랜치와 PR만 사용한다. Codex는 추적 SQLite DB를 절대 변경하지 않고 migration 파일만 PR로 제안할 수 있다. 텍스트 문서도 같은 파일 동시 편집은 피한다.

### Claude → Codex

Claude는 PC에서 사용자와 함께 검증하므로 `main`에 직접 commit·push하고 작업서버와 DB 변경을 담당한다. Codex는 작업별 브랜치와 PR을 사용하며 DB 파일을 건드리지 않는다. 시장조사 문서는 둘 다 수정할 수 있으나 작업 전 최신 변경을 반영한다. 공통 규칙은 루트 `AGENTS.md`를 기준으로 삼는다.

### 합의

위 역할 분담을 채택했다. 세부 실행 규칙은 `AGENTS.md`에 반영했다.
