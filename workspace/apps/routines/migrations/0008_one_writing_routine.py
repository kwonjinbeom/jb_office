"""글쓰기 루틴 하나로 (2026-10-16 사용자: 글쓰기는 티스토리·네이버 구분이 사라졌다. 하루 11편, 운영 화면 사이트 컨셉에 맞게).

- '티스토리 글쓰기' 루틴 → '글쓰기' (키 writing). 평가·이력·실행 기록은 그대로 따라간다.
- '네이버 글쓰기' 루틴 → 휴지통 (7일 동안 복원 가능). 지우지 않는다.
"""
from django.db import migrations
from django.utils import timezone

WRITING = dict(
    key="writing", name="글쓰기", url_name="posts:index",
    task="운영 사이트 컨셉에 맞게, 고른 분류별 원고 쓰기", output="포스팅자동화/원고/T번호_이름/원고.md",
    daily=11, unit="편", prompt_doc="일일루틴/프롬프트/writing.md", data="picks,sites,existing,categories",
)


def forward(apps, schema_editor):
    Routine = apps.get_model("routines", "Routine")
    TrashEntry = apps.get_model("core", "TrashEntry")
    if not Routine.objects.filter(key="writing").exists():
        r = Routine.objects.filter(key="tistory", deleted_at__isnull=True).first()
        if r is not None:
            for field, value in WRITING.items():
                setattr(r, field, value)
            r.save()
    naver = Routine.objects.filter(key="naver", deleted_at__isnull=True).first()
    if naver is not None:
        now = timezone.now()
        if not TrashEntry.objects.filter(model_label="routines.routine", object_key=str(naver.pk)).exists():
            TrashEntry.objects.create(model_label="routines.routine", object_key=str(naver.pk), title=naver.name,
                                      section="일일루틴", deleted_at=now, members={"routines.routine": [naver.pk]})
        naver.deleted_at = now
        naver.save(update_fields=["deleted_at"])


class Migration(migrations.Migration):
    dependencies = [("routines", "0007_writing_picks"), ("core", "0003_menu_setting")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
