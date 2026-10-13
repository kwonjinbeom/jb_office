# Claude와 Codex 공동 작업 규칙

이 파일이 저장소의 AI 협업 규칙에 대한 단일 기준 문서다. Claude와 Codex는 작업 전에 반드시 읽는다. 논의 기록은 `AI_COLLABORATION.md`에 둔다.

## 역할과 브랜치

### Claude (PC)

- 사용자가 PC에서 결과를 바로 확인하는 통합 담당자다.
- 사용자 동석 아래 `main`에 직접 commit·push할 수 있다.
- 작업 전에 `git pull --ff-only origin main`을 실행하고 working tree가 깨끗한지 확인한다.
- 같은 파일을 수정하는 Codex PR이 진행 중이면 먼저 그 PR을 병합하거나 작업 범위를 조정한다.
- Django 검사와 사용자 화면 확인을 마친 뒤 변경을 반영한다.
- `.claude/settings.json`의 Stop 자동 동기화 훅은 사용자의 선택에 따라 유지한다. 이 훅은 모든 변경을 stage하므로 Claude 실행 전 다른 작업자의 미커밋 변경이 없어야 한다.

### Codex (Cloud)

- `main`에 직접 commit·push하지 않는다.
- 최신 `origin/main`에서 `codex/<작업명>` 브랜치를 만들고 작업별 PR을 올린다.
- PR에 변경 내용, 실행한 검사, 실패·미실행 검사와 남은 위험을 기록한다.
- 애플리케이션의 자동 Git 동기화와 수동 동기화 엔드포인트를 사용하지 않는다.
- 다른 작업자의 변경을 되돌리거나 덮어쓰지 않는다.

## SQLite와 마이그레이션

- `작업서버/db.sqlite3`의 유일한 작성자는 PC의 Claude와 사용자다.
- Codex는 `작업서버/db.sqlite3`를 어떤 작업에서도 수정, 교체, 삭제, stage하지 않는다.
- Codex는 `migrate`, `seed_ideas`처럼 추적 DB를 변경하는 명령을 실행하지 않는다.
- Codex는 `migrate --check --plan` 같은 읽기 전용 검사와 임시 테스트 DB를 사용할 수 있다.
- 스키마 변경에 필요한 Django migration 파일을 생성·수정하는 것은 허용된다. 해당 PR에는 PC에서 실제 DB 적용이 필요하다고 명시한다.

## 문서 협업

- `시장조사/` 같은 텍스트 문서는 둘 다 수정할 수 있다.
- 작업 전에 최신 `main`을 반영하고, 같은 문서를 동시에 수정하지 않는다. Git의 자동 병합을 보장된 것으로 간주하지 않는다.
- 충돌이 생기면 내용을 임의로 버리지 말고 사용자에게 양쪽 변경을 설명한다.

## 공통 안전 규칙

- force push, hard reset, 다른 작업자의 commit 수정은 사용자의 명시적 요청 없이 하지 않는다.
- 실제로 동일한 로컬 체크아웃을 공유한다면 Claude와 다른 도구를 동시에 실행하지 않는다.
- 비밀값을 저장소, 로그, 문서에 기록하지 않는다.
