"""일일루틴 처음 세 줄: 일일 아이디어 · 티스토리 글쓰기 · 네이버 글쓰기 (2026-10-16 사용자).

로컬 = 이 PC 저장소에서 claude (사이트를 직접 볼 수 있음, main 에 push).
클라우드 = 클라우드 세션에 직접 보냄 (티스토리·네이버를 제대로 못 봄 → 이미 있는 글 목록을 넣어 겹침을 피함, PR 로 올림).
"""
from django.db import migrations

NO_PUBLISH = "발행·로그인·자동 게시는 하지 않는다. 고르고 손질해 발행하는 건 내가 한다."

IDEA_LOCAL = """# 일일루틴 · 일일 아이디어 — {날짜} (로컬 PC)

이 PC 의 jb_office 저장소에서 진행한다. 웹 검색과 사이트 확인 모두 할 수 있다.

- 먼저 AGENTS.md 를 읽는다.
- 하루 양: 후보 {하루양}.
- 이전 날짜 후보와 겹치지 않게 시장조사/일일아이디어/*.json 을 직접 확인한다.
- 끝나면 결과 파일을 main 에 커밋·push 한다 (서버 반영은 웹훅이 자동).

{검색표준}"""

IDEA_CLOUD = """# 일일루틴 · 일일 아이디어 — {날짜} (클라우드)

클라우드 세션(jb_office 저장소)에서 진행한다. 막힌 사이트는 상세 문서에 '확인 못 함'으로 적고 넘어간다.

- 먼저 AGENTS.md 를 읽는다.
- 하루 양: 후보 {하루양}.
- 최근 후보 (겹치지 않게):
{기존글}
- 끝나면 새 브랜치에 커밋하고 main 으로 PR 을 만든다.

{검색표준}"""

WRITE_LOCAL = """# 일일루틴 · {메뉴} — {날짜} (로컬 PC)

이 PC 의 jb_office 저장소에서 진행한다. 브라우저·웹으로 블로그를 직접 볼 수 있다.

## 사이트
{사이트}

## 할 일
1. AGENTS.md, workspace/{가이드}, 콘텐츠/블로그_카페/포스팅자동화/원고/README.md 를 읽는다.
2. 각 블로그의 최근 글과 원고 폴더({폴더})를 직접 확인해 주제가 겹치지 않게 한다.
3. 오늘 트렌드·검색 수요를 찾아 원고 {하루양}을 쓴다. 사이트 컨셉과 체크에 맞게 나눠 배정하고, 원고 위쪽 제작 정보에 어느 사이트용인지 적는다.
4. 저장: {폴더}/{접두}번호_짧은이름/원고.md (원고/README.md 형식, 번호는 이어서).
5. main 에 커밋·push 한다.

""" + NO_PUBLISH + " ({메뉴} › 원고 가져오기)"

WRITE_CLOUD = """# 일일루틴 · {메뉴} — {날짜} (클라우드)

클라우드 세션(jb_office 저장소)에서 진행한다. 클라우드에서는 블로그를 제대로 볼 수 없으니 사이트를 열지 말고, 아래 '이미 있는 글'로 겹침을 피한다.

## 사이트
{사이트}

## 이미 있는 글 (겹치지 않게)
{기존글}

## 할 일
1. AGENTS.md, workspace/{가이드}, 콘텐츠/블로그_카페/포스팅자동화/원고/README.md 를 읽는다.
2. 웹 검색으로 오늘 트렌드·검색 수요를 찾아 원고 {하루양}을 쓴다. 사이트 컨셉과 체크에 맞게 나눠 배정하고, 원고 위쪽 제작 정보에 어느 사이트용인지 적는다.
3. 숫자·날짜는 원 출처에서 확인하고, 확인 못 한 것은 원고 제작 정보에 적는다.
4. 저장: {폴더}/{접두}번호_짧은이름/원고.md (원고/README.md 형식, 번호는 저장소에 있는 것 다음부터).
5. 새 브랜치에 커밋하고 main 으로 PR 을 만든다.

""" + NO_PUBLISH


def _write(text, menu, guide, folder, prefix):
    return (text.replace("{메뉴}", menu).replace("{가이드}", guide)
            .replace("{폴더}", folder).replace("{접두}", prefix))


ROUTINES = [
    dict(key="daily_ideas", name="일일 아이디어", url_name="daily_ideas:list", task="트렌드·검색으로 아이디어 후보 찾기",
         output="시장조사/일일아이디어/날짜.json + 상세 문서", daily=10, unit="개",
         prompt_local=IDEA_LOCAL, prompt_cloud=IDEA_CLOUD),
    dict(key="tistory", name="티스토리 글쓰기", url_name="writing:list", task="트렌드 주제 찾기 → 사이트별 원고 쓰기",
         output="포스팅자동화/원고/T번호_이름/원고.md", daily=4, unit="편",
         prompt_local=_write(WRITE_LOCAL, "티스토리 글쓰기", "TISTORY_WRITER.md", "콘텐츠/블로그_카페/포스팅자동화/원고", "T"),
         prompt_cloud=_write(WRITE_CLOUD, "티스토리 글쓰기", "TISTORY_WRITER.md", "콘텐츠/블로그_카페/포스팅자동화/원고", "T")),
    dict(key="naver", name="네이버 글쓰기", url_name="naver_writing:list", task="방문자용 주제 찾기 → 원고 쓰기",
         output="포스팅자동화/네이버원고/N번호_이름/원고.md", daily=2, unit="편",
         prompt_local=_write(WRITE_LOCAL, "네이버 글쓰기", "NAVER_WRITER.md", "콘텐츠/블로그_카페/포스팅자동화/네이버원고", "N"),
         prompt_cloud=_write(WRITE_CLOUD, "네이버 글쓰기", "NAVER_WRITER.md", "콘텐츠/블로그_카페/포스팅자동화/네이버원고", "N")),
]


def forward(apps, schema_editor):
    Routine = apps.get_model("routines", "Routine")
    for order, data in enumerate(ROUTINES, start=1):
        Routine.objects.get_or_create(key=data["key"], defaults={**data, "order": order})


class Migration(migrations.Migration):
    dependencies = [("routines", "0001_initial")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
