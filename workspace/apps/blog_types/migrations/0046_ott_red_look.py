"""black_lukey › 영화·OTT 공개 글 모양을 '빨강 정갈'로 (2026-10-28 사용자: 지금 구조 그대로, 작품 제목은 막대에 빨강만,
나머지는 눈잎 정갈의 표·카드 디테일에 빨강 — 도안 콘텐츠/블로그_카페/memorily_네이버/도안_영화OTT_빨강.html 을 보고 "이 양식으로").

1. SiteCategory.look 선택지에 red (site_templates.red_look 이 네이버 붙여넣기 HTML 을 그린다).
2. 영화·OTT 공개 look = red, 컨셉 끝에 '화면 모양' 한 묶음 (글쓰기 안내문·변환 요청문에 들어간다). 이미 있으면 건드리지 않는다.
지우는 데이터 없음. 되돌리면 look 을 비우고 그 묶음만 뺀다.
"""
from django.db import migrations, models

NAME = "영화·OTT 공개"
MARK = "화면 모양 (빨강 정갈"
BLOCK = """화면 모양 (빨강 정갈 — 2026-10-28 사용자. 도안 콘텐츠/블로그_카페/memorily_네이버/도안_영화OTT_빨강.html. 붙여 넣는 HTML 이 그린다 — 원고·변환본에는 꾸밈 코드를 넣지 않는다):
- 순서·문장·카드는 위 글 모양 그대로. 맨 위 인용(>) 2~3문장은 '한눈에' 연회색 상자가 된다.
- 보통 `## 소제목`(공개 달력 · 뭐부터 볼까)은 앞에 01·02 번호가 저절로 붙는다 — 번호·이모지를 쓰지 않는다.
- 작품은 `## 작품 이름 · 공개일` 바로 아래(다음 소제목 전)에 `::: 작품` 카드가 있어야 빨간 막대 작품 제목이 된다. 카드 이름표는 `이모지 이름표 | 값` 그대로.
- 표 머리는 연회색 바탕·빨간 글자, 숫자 칸 오른쪽 정렬. 굵게는 빨강 — 한 단락에 한 번 이하."""
CHOICES = [("", "기본"), ("yudi", "유디 메모지"), ("wp_mountain", "워드프레스 · 산"), ("wp_car", "워드프레스 · 자동차"),
           ("wp_travel", "워드프레스 · 여행"), ("nunip", "눈잎 정갈 (남색·회색)"), ("red", "빨강 정갈 (네이버)")]


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(blog__platform="naver", name=NAME, parent=None, deleted_at__isnull=True):
        fields = []
        if cat.look != "red":
            cat.look = "red"
            fields.append("look")
        if MARK not in cat.concept:
            cat.concept = (cat.concept.rstrip() + "\n" + BLOCK).strip()
            fields.append("concept")
        if fields:
            cat.save(update_fields=fields)


def backward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(blog__platform="naver", name=NAME, parent=None, deleted_at__isnull=True):
        cat.concept = cat.concept.replace("\n" + BLOCK, "").replace(BLOCK, "").strip()
        cat.look = "" if cat.look == "red" else cat.look
        cat.save(update_fields=["concept", "look"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0045_nunip_clean_look")]
    operations = [
        migrations.AlterField(
            model_name="sitecategory", name="look",
            field=models.CharField("글 모양", max_length=20, blank=True, choices=CHOICES,
                                   help_text="붙여넣는 HTML 의 화면 모양 (가운데 정렬·메모지 상자 등). 하위 카테고리도 따른다")),
        migrations.RunPython(forward, backward),
    ]
