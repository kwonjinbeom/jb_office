"""black_lukey › 지역 놀거리 · 축제·행사 표 모양 (2026-10-28 사용자: 예시안에서 "일반 표는 1번 가는 선, 장소 카드는 4번 모노 초록 포인트,
축제·행사는 주황 포인트"). 표 두 종류만 바꾸고 글의 다른 모양은 그대로 — site_templates.naver_line 이 그린다.

1. SiteCategory.look 선택지에 line_green · line_orange.
2. 지역 놀거리 look = line_green, 축제·행사 look = line_orange, 컨셉 끝에 '화면 모양' 한 줄. 이미 있으면 건드리지 않는다.
지우는 데이터 없음. 되돌리면 look 을 비우고 그 줄만 뺀다.
"""
from django.db import migrations, models

CATS = {"지역 놀거리": ("line_green", "초록"), "축제·행사": ("line_orange", "주황")}
MARK = "화면 모양 (가는 선 표"
LINE = ("화면 모양 (가는 선 표 · 모노 카드, 2026-10-28 사용자): 표는 변환이 그린다 — 일반 표는 세로줄 없이 위아래 굵은 선과 가는 가로줄, "
        "정보 카드는 연회색 이름표 칸에 머리 줄만 {color} 윗줄·라벨. 원고는 지금처럼 `| 표 |` 와 `::: 장소 | 이름` 으로만 쓰고 꾸밈 코드는 넣지 않는다. "
        "비용 표의 마지막 줄은 `| 합계 | … |` 로 두면 합계 줄로 그려진다.")
CHOICES = [("", "기본"), ("yudi", "유디 메모지"), ("wp_mountain", "워드프레스 · 산"), ("wp_car", "워드프레스 · 자동차"),
           ("wp_travel", "워드프레스 · 여행"), ("nunip", "눈잎 정갈 (남색·회색)"), ("red", "빨강 정갈 (네이버)"),
           ("line_green", "네이버 · 가는 선 표 + 초록 카드"), ("line_orange", "네이버 · 가는 선 표 + 주황 카드")]


def forward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for name, (look, color) in CATS.items():
        for cat in SiteCategory.objects.filter(blog__platform="naver", name=name, parent=None, deleted_at__isnull=True):
            fields = []
            if cat.look != look:
                cat.look = look
                fields.append("look")
            if MARK not in cat.concept:
                cat.concept = (cat.concept.rstrip() + "\n" + LINE.format(color=color)).strip()
                fields.append("concept")
            if fields:
                cat.save(update_fields=fields)


def backward(apps, schema_editor):
    SiteCategory = apps.get_model("blog_types", "SiteCategory")
    for name, (look, color) in CATS.items():
        line = LINE.format(color=color)
        for cat in SiteCategory.objects.filter(blog__platform="naver", name=name, parent=None, deleted_at__isnull=True):
            cat.concept = cat.concept.replace("\n" + line, "").replace(line, "").strip()
            cat.look = "" if cat.look == look else cat.look
            cat.save(update_fields=["concept", "look"])


class Migration(migrations.Migration):
    dependencies = [("blog_types", "0046_ott_red_look")]
    operations = [
        migrations.AlterField(
            model_name="sitecategory", name="look",
            field=models.CharField("글 모양", max_length=20, blank=True, choices=CHOICES,
                                   help_text="붙여넣는 HTML 의 화면 모양 (가운데 정렬·메모지 상자 등). 하위 카테고리도 따른다")),
        migrations.RunPython(forward, backward),
    ]
