"""2026-10-20 발행 글(memorily/224447962821)로 확인: 네이버도 서식 그대로 붙이면 사진 주소가 사진으로 옮겨진다.
0005 에서 넣은 '붙인 뒤 내려받아 올린다' 문장만 바로잡는다. 화면에서 고쳤으면 그대로 둔다."""
from django.db import migrations

OLD = ("사진·스티커·지도·링크 카드는 붙여넣기로 옮겨지지 않는다. 사진은 변환 때 무료 사진(Unsplash·Pexels·Pixabay) 주소로 넣어 두고 "
       "(변환 화면에 보인다), 붙인 뒤 내려받아 그 자리에 올린다.")
NEW = ("사진은 변환 때 무료 사진(Unsplash·Pexels·Pixabay) 주소로 넣는다. 서식 그대로 붙이면 사진으로 옮겨진다. "
       "스티커·지도·링크 카드는 붙여넣기로 옮겨지지 않는다.")


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
    dependencies = [("site_templates", "0005_naver_photos")]
    operations = [migrations.RunPython(forward, backward)]
