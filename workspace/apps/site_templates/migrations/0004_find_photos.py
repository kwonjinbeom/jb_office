"""2026-10-20 사용자: 변환 때 사진 자리를 비워 두지 말고 무료 사진을 찾아 넣는다 (prompt.PHOTOS).
붙여넣기 포맷의 '사진은 [사진: 설명] 한 줄 자리만' 문장만 바꾼다. 그 문장이 없으면(화면에서 고쳤으면) 그대로 둔다."""
from django.db import migrations

CHANGE = {
    "tistory": (
        "사진은 [사진: 설명] 한 줄 자리만 둔다 (에디터에서 직접 올려야 대표 이미지·목록 썸네일이 잡힌다). 한 장 20MB 까지.",
        "사진은 변환 때 무료 사진(Unsplash·Pexels·Pixabay) 주소로 넣는다. 대표 이미지·목록 썸네일은 에디터에서 직접 올린 사진만 "
        "잡히니 첫 사진은 내려받아 올린다. 한 장 20MB 까지.",
    ),
    "blogger": (
        "사진은 [사진: 설명] 한 줄 자리만 (직접 올린다, 첫 사진이 목록 썸네일). 외부 이미지는 https 주소만.",
        "사진은 변환 때 무료 사진(Unsplash·Pexels·Pixabay) https 주소로 넣는다 (첫 사진이 목록 썸네일).",
    ),
}


def forward(apps, schema_editor):
    PlatformFormat = apps.get_model("site_templates", "PlatformFormat")
    for platform, (old, new) in CHANGE.items():
        for fmt in PlatformFormat.objects.filter(platform=platform, guide__contains=old):
            fmt.guide = fmt.guide.replace(old, new)
            fmt.save(update_fields=["guide"])


def backward(apps, schema_editor):
    PlatformFormat = apps.get_model("site_templates", "PlatformFormat")
    for platform, (old, new) in CHANGE.items():
        for fmt in PlatformFormat.objects.filter(platform=platform, guide__contains=new):
            fmt.guide = fmt.guide.replace(new, old)
            fmt.save(update_fields=["guide"])


class Migration(migrations.Migration):
    dependencies = [("site_templates", "0003_paste_research")]
    operations = [migrations.RunPython(forward, backward)]
