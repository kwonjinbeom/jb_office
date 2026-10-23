"""사이트 카테고리 '글 모양' (2026-10-23 사용자): 눈잎 › 일본 여행은 유디 블로그의 화면 짜임으로.

사용자: 유디 블로그는 글꼴·색·배치 같은 화면 짜임이 좋았던 것인데, 내용 구성만 따라 해서 평소 다른 블로그와 똑같아졌다 →
이 카테고리만 화면 모양을 통째로 바꾼다 (site_templates.looks.yudi). 컨셉 맨 끝에 '화면 모양' 단락을 더한다. 지우는 데이터 없음.
"""
from django.db import migrations, models

LOOK = "\n".join([
    "",
    "화면 모양 (2026-10-23 사용자 — 유디 블로그의 화면 짜임, 붙여 넣는 HTML 이 그린다):",
    "- 가운데 정렬, 한 줄에 한 호흡 (짧게 끊어 줄바꿈, 2~4줄이 한 단락, 단락 사이 넉넉히).",
    "- 나눔스퀘어 본문, 굵은 글씨 대신 청록 글자 · 가장 중요한 한 구절은 연두 형광펜(==…==).",
    "- 소제목은 회색 큰따옴표 + 나눔명조 + 가는 밑줄 (번호 단 짧은 물음), 큰 단락 사이 가운데 사선(---).",
    "- 정보는 모서리 접힌 메모지 상자(청록 글자) · 목차는 가운데 좁은 표(머리 칸 연두) · 사진은 2장씩 콜라주.",
])


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(blog__name="눈잎", name="일본 여행", deleted_at__isnull=True):
        cat.look = "yudi"
        if "화면 모양" not in cat.concept:
            cat.concept = cat.concept.rstrip() + "\n" + LOOK
        cat.save(update_fields=["look", "concept"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0022_nunip_japan_concept")]
    operations = [
        migrations.AddField(
            model_name="sitecategory", name="look",
            field=models.CharField(blank=True, choices=[("", "기본"), ("yudi", "유디 메모지")], max_length=20,
                                   help_text="붙여넣는 HTML 의 화면 모양 (가운데 정렬·메모지 상자 등). 하위 카테고리도 따른다",
                                   verbose_name="글 모양"),
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
