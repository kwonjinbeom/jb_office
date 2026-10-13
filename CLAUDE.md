# Claude 저장소 지침

작업을 시작하기 전에 `AI_COLLABORATION.md`를 읽고 브랜치, Git 안전, SQLite 단일 작성자 규칙을 따른다.

사용자의 선택에 따라 `.claude/settings.json`의 Stop 자동 동기화 훅은 유지한다. 작업을 시작하기 전에 다음 조건을 모두 확인한다.

- 현재 브랜치는 `main`이 아니라 `claude/<작업명>`이다.
- 같은 이름의 원격 브랜치가 이미 생성되어 있다.
- 현재 체크아웃에는 사용자나 다른 AI의 미커밋 변경이 없다.
- Codex가 동일한 물리적 체크아웃을 동시에 사용하지 않는다.

Stop 훅은 모든 변경을 `git add -A`로 stage하므로 위 조건을 만족하지 않으면 작업을 시작하지 않고 사용자에게 알린다. 결과는 작업별 PR로 `main`에 병합한다.

`AI_COLLABORATION.md`의 `Claude → Codex` 항목에 검토 결과나 수정 제안을 남긴다.
