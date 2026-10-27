"""워드프레스 붙여넣기 포맷의 낡은 줄 두 개를 지금 동작에 맞춘다 (2026-10-27 정리).

- 글모양.css 는 '추가 CSS' 가 아니라 붙이는 블록 안 <style> 로 함께 들어간다 (wp_looks · paste, 2026-10-26).
- 요약(발췌)은 맨 위 리드가 되고, 리드 길이는 카테고리 컨셉(2~3문장)을 따른다.
사용자가 이미 고친 줄은 건드리지 않는다. 지우는 데이터 없음.
"""
from django.db import migrations

CHANGES = (
    ("모양은 외모 › 사용자 정의하기 › 추가 CSS 에 한 번 넣은 글모양.css 가 입힌다 (콘텐츠/블로그_카페/워드프레스/글모양.css). 변환본에는 꾸밈 코드를 넣지 않는다.",
     "모양은 글모양.css (콘텐츠/블로그_카페/워드프레스/글모양.css) 가 붙이는 블록 안에 함께 들어가 입힌다. 변환본에는 꾸밈 코드를 넣지 않는다."),
    ("제목은 60자 안쪽, 슬러그는 영문 짧게, 요약(발췌)에 소개 한두 문장.",
     "제목은 60자 안쪽, 슬러그는 영문 짧게. 요약(발췌)은 맨 위 리드(카테고리 컨셉대로 2~3문장)가 된다."),
)


def forward(apps, schema_editor):
    PlatformFormat = apps.get_model("site_templates", "PlatformFormat")
    for fmt in PlatformFormat.objects.filter(platform="wordpress"):
        guide = fmt.guide
        for old, new in CHANGES:
            if old in guide:
                guide = guide.replace(old, new, 1)
        if guide != fmt.guide:
            fmt.guide = guide
            fmt.save(update_fields=["guide"])


class Migration(migrations.Migration):
    dependencies = [("site_templates", "0010_naver_parking_address"), ("blog_types", "0041_photo_counts")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
