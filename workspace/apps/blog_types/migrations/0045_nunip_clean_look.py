"""눈잎 › 청년·신혼 정책 · 주택 공고 · 공모주 · 생활 글 모양을 '눈잎 정갈'로 (2026-10-28 사용자: 미리캔버스 강연 발표자료를
블로그 글에 녹인 도안을 보고 "좋다, 일본여행을 제외한 네 카테고리에 앞으로 적용"). 일본 여행·일상은 유디 메모지 그대로.

1. SiteCategory.look 선택지에 nunip (site_templates.nunip_look 이 그린다).
2. 네 카테고리 look = nunip, 컨셉 끝에 '화면 모양' 한 묶음 (글쓰기 안내문·변환 요청문에 들어간다). 이미 있으면 건드리지 않는다.
지우는 데이터 없음. 되돌리면 look 을 비우고 그 묶음만 뺀다.
"""
from django.db import migrations, models

CATS = ["청년·신혼 정책", "주택 공고", "공모주", "생활"]
MARK = "화면 모양 (눈잎 정갈"
BLOCK = """화면 모양 (눈잎 정갈 — 남색 포인트·연회색·가는 줄, 2026-10-28 사용자. 도안 콘텐츠/블로그_카페/눈잎_티스토리/도안_생활정책_남색회색.html. 붙여 넣는 HTML 이 그린다 — 원고·변환본에는 꾸밈 코드를 넣지 않는다):
- 맨 위 인용(>) 2~3문장은 '한눈에_' 연회색 상자가 된다. 기준일(○월 ○일 ○○ 발표·공고 기준)은 여기에.
- `## 소제목` 은 짧은 말로, 번호·이모지 없이 (앞의 01·02 번호와 끝의 '_' 는 저절로). 바로 다음 줄에 `*한 줄 설명*` — 그 소제목의 답을 20자 안팎으로.
- 접수일·신청처·환불일 같은 '이름표 + 값' 줄은 `- **접수** 11월 16일(월) 09:00~17:30` 목록으로 (이름표는 짧게, 마침표 없이) — 가는 줄로 나뉜 이름표 줄이 된다.
- 표 머리는 연회색 바탕·남색 글자, 금액 칸은 오른쪽 정렬. 굵게는 한 단락에 한 번 이하. 이모지·형광펜·색 글자는 쓰지 않는다."""
CHOICES = [("", "기본"), ("yudi", "유디 메모지"), ("wp_mountain", "워드프레스 · 산"), ("wp_car", "워드프레스 · 자동차"),
           ("wp_travel", "워드프레스 · 여행"), ("nunip", "눈잎 정갈 (남색·회색)")]


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(blog__name="눈잎", name__in=CATS, parent=None, deleted_at__isnull=True):
        fields = []
        if cat.look != "nunip":
            cat.look = "nunip"
            fields.append("look")
        if MARK not in cat.concept:
            cat.concept = (cat.concept.rstrip() + "\n" + BLOCK).strip()
            fields.append("concept")
        if fields:
            cat.save(update_fields=fields)


def backward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for cat in SiteCategory.objects.filter(blog__name="눈잎", name__in=CATS, parent=None, deleted_at__isnull=True):
        cat.concept = cat.concept.replace("\n" + BLOCK, "").replace(BLOCK, "").strip()
        cat.look = "" if cat.look == "nunip" else cat.look
        cat.save(update_fields=["concept", "look"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0044_travel_ticket_look")]
    operations = [
        migrations.AlterField(
            model_name="sitecategory", name="look",
            field=models.CharField("글 모양", max_length=20, blank=True, choices=CHOICES,
                                   help_text="붙여넣는 HTML 의 화면 모양 (가운데 정렬·메모지 상자 등). 하위 카테고리도 따른다")),
        migrations.RunPython(forward, backward),
    ]
