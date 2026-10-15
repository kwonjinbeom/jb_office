# Claude 저장소 지침

> **⚠️ 서버 반영·migrate 는 main push 때 웹훅이 자동으로 한다. 사용자에게 '서버 코드 갱신' 버튼이나 서버 `migrate` 를 절대 안내하거나 묻지 않는다.** push 뒤 `gh api` 로 웹훅 응답(`deployed <커밋>`)을 직접 확인하고, 실패했을 때만 알린다. (AGENTS.md 맨 위 상자)
>
> **⚠️ PR 병합도 묻지 않는다.** check·테스트·화면 확인이 끝나면 바로 `gh pr merge` → 서버 반영 확인 → 결과만 알린다. "합칠까요?" 로 멈추지 않는다 — 잘못되면 되돌리면 된다. 예외는 서버 데이터를 지우는 migration 뿐 (지워지는 것을 먼저 말한다). gh 는 `C:\Program Files\GitHub CLI\gh.exe`.

작업 전에 루트 `AGENTS.md`를 읽고 이를 협업 규칙의 단일 기준으로 따른다. 논의 경위가 필요하면 `AI_COLLABORATION.md`를 확인한다.

Claude는 사용자와 PC에서 검증하며 `main` 통합과 `workspace/` 코드·migration을 담당한다. 데이터 원본은 PythonAnywhere 서버 DB이며 Git에 없다 (`workspace/DEPLOY.md`). Stop 자동 동기화 훅을 실행하기 전에 최신 `main`, 깨끗한 working tree, 겹치는 Codex PR이 없는지를 확인한다.
