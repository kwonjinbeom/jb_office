# Claude 저장소 지침

작업을 시작하기 전에 `AI_COLLABORATION.md`를 읽고 브랜치, Git 안전, SQLite 단일 작성자 규칙을 따른다.

특히 `.claude/settings.json`의 Stop 훅이 실행하는 자동 `git add -A`·commit·pull·push는 다중 AI 협업과 충돌한다. 병렬 협업 중에는 자동 동기화를 비활성화하고 작업별 브랜치와 PR을 사용한다.

`AI_COLLABORATION.md`의 `Claude → Codex` 항목에 검토 결과나 수정 제안을 남긴다.
