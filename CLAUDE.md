# Claude 저장소 지침

작업 전에 루트 `AGENTS.md`를 읽고 이를 협업 규칙의 단일 기준으로 따른다. 논의 경위가 필요하면 `AI_COLLABORATION.md`를 확인한다.

Claude는 사용자와 PC에서 검증하며 `main` 통합과 추적 SQLite DB 변경을 담당한다. Stop 자동 동기화 훅을 실행하기 전에 최신 `main`, 깨끗한 working tree, 겹치는 Codex PR이 없는지를 확인한다.
