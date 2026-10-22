"""사이트마다 글쓰기 타겟을 확실히 (2026-10-22 사용자). 모니터링에 한 줄로 보인다.

- 티스토리 memorily: 사용자가 직접 쓴다 (애니 등) → 글쓰기 루틴 대상에서 뺀다 (routine=False).
- 눈잎: 주택 공고 · 청년·신혼 정책 · 공모주 · 엔화 · 일본 중심 해외여행 알짜.
- 네이버 black_lukey: 지역 놀거리·축제 · 신제품·영화 출시 · 인기 세일 이벤트 · AI 소식.
- 밤밤 (https://bambam2222.blogspot.com/): 코스피·나스닥 그날 이유 각각 · 가끔 상품 추천. 운영으로 바꿔 모니터링에 넣는다.
"""
from django.db import migrations, models

CONTENT = {
    "memorily": "직접 쓰는 글 (애니·개발) — 글쓰기 루틴 제외",
    "눈잎": "주택 공고 · 청년·신혼 정책 · 공모주 · 엔화 · 일본 중심 해외여행 알짜",
    "black_lukey": "지역 놀거리·축제 · 신제품·영화 출시 · 인기 세일 · AI 소식",
    "밤밤": "코스피·나스닥 그날 이유 (각각) · 가끔 상품 추천",
}


def forward(apps, schema_editor):
    Blog = apps.get_model("blog_rules", "Blog")
    for name, content in CONTENT.items():
        Blog.objects.filter(name=name).update(content=content)
    Blog.objects.filter(name="memorily", platform="tistory").update(routine=False)
    Blog.objects.filter(name="밤밤").update(status="active", address="https://bambam2222.blogspot.com/", daily=2)


class Migration(migrations.Migration):
    dependencies = [("blog_rules", "0008_site_day")]
    operations = [
        migrations.AddField(
            model_name="blog", name="routine",
            field=models.BooleanField("글쓰기 루틴", default=True,
                                      help_text="일일루틴 글쓰기가 이 사이트 원고를 쓴다 (끄면 사용자가 직접 쓰는 사이트)"),
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
