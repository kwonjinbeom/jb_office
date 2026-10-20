"""2026-10-20 사용자: 네이버 글도 변환 때 무료 사진을 찾아 넣는다 (prompt.PHOTO_PLATFORMS).
네이버 붙여넣기 포맷의 사진 문장만 바꾼다. 그 문장이 없으면(화면에서 고쳤으면) 그대로 둔다."""
from django.db import migrations

OLD = "사진·스티커·지도·링크 카드는 붙여넣기로 옮겨지지 않는다. [사진: 설명] 한 줄 자리만 둔다."
NEW = ("사진·스티커·지도·링크 카드는 붙여넣기로 옮겨지지 않는다. 사진은 변환 때 무료 사진(Unsplash·Pexels·Pixabay) 주소로 넣어 두고 "
       "(변환 화면에 보인다), 붙인 뒤 내려받아 그 자리에 올린다.")


def forward(apps, schema_editor):
    PlatformFormat = apps.get_model("site_templates", "PlatformFormat")
    for fmt in PlatformFormat.objects.filter(platform="naver", guide__contains=OLD):
        fmt.guide = fmt.guide.replace(OLD, NEW)
        fmt.save(update_fields=["guide"])


def backward(apps, schema_editor):
    PlatformFormat = apps.get_model("site_templates", "PlatformFormat")
    for fmt in PlatformFormat.objects.filter(platform="naver", guide__contains=NEW):
        fmt.guide = fmt.guide.replace(NEW, OLD)
        fmt.save(update_fields=["guide"])


class Migration(migrations.Migration):
    dependencies = [("site_templates", "0004_find_photos")]
    operations = [migrations.RunPython(forward, backward)]
