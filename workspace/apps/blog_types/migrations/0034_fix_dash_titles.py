"""변환본 제목에서 ? 로 깨진 줄표를 되살린다 (2026-10-26 사용자: 워드프레스 제목이 모두 ?).

PC 터미널 claude 가 제목을 curl 명령줄로 보냈는데, Windows 가 명령줄 글자를 cp949 로 바꾸면서 cp949 에 없는 — 가 ? 가 됐다
(본문은 파일로 보내 멀쩡했다). 이제 제목·태그도 파일로 보낸다 (site_templates.prompt.launcher).
원문 제목에 — 가 있고 변환본 제목에 ' ? ' 가 있는 것만 ' — ' 로 고친다 (2026-10-26 서버: 워드프레스 두 편). 지우는 데이터 없음.
"""
from django.db import migrations


def forward(apps, schema_editor):
    Placement = apps.get_model("blog_types", "Placement")
    for pl in Placement.objects.filter(converted_title__contains=" ? ").select_related("tistory_post", "naver_post"):
        post = pl.tistory_post or pl.naver_post
        if post is not None and "—" in post.title:
            pl.converted_title = pl.converted_title.replace(" ? ", " — ")
            pl.save(update_fields=["converted_title"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0033_market_notes_split")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
