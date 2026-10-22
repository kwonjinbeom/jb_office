"""AI 소식 원고 정리 (2026-10-22 사용자): 주 7편 설정일 때 한 번에 6편이 쓰였다 → 가장 최근 T108 만 남기고 5편은 휴지통.

T102·T103·T105·T106·T107 (티스토리·네이버 어느 표든, 넣은 곳 포함). 원고 폴더도 지워 다시 들어오지 않게 했다. 7일 안 복원 가능.
"""
from django.db import migrations
from django.utils import timezone

TITLES = [
    "AI 소식: OpenAI 모델 Google Cloud 입성, Gemini 앱 모델 접근 정리 (2026-10-22)",
    "코딩 에이전트 소식 3가지 — Copilot 모델 교체, Claude Code 자동 모드 설정, Codex 중간 개입 (2026-10-22)",
    "AI 영상 새 모델 FLUX 3 Max, 10초 클립 12초 생성 (2026-10 넷째 주)",
    "업무용 AI 소식 3가지: Notion 에이전트 24시간, Docs 음성 작성, Gemini Customize (2026-10-22)",
    "크래프톤 라온-1 미니 공개, DeepSeek 추론 프레임워크 공개 (AI 소식 2026-10-22)",
]
SECTIONS = {"writing": "티스토리 글쓰기 · 임시글", "naver_writing": "네이버 글쓰기 · 임시글"}


def forward(apps, schema_editor):
    TrashEntry = apps.get_model("core", "TrashEntry")
    Placement = apps.get_model("blog_types", "Placement")
    now = timezone.now()
    for label, section in SECTIONS.items():
        Post = apps.get_model(label, "Post")
        field = "tistory_post" if label == "writing" else "naver_post"
        for post in Post.objects.filter(title__in=TITLES, deleted_at__isnull=True):
            places = list(Placement.objects.filter(**{field: post}, deleted_at__isnull=True).values_list("pk", flat=True))
            members = {f"{label}.post": [post.pk], **({"blog_types.placement": places} if places else {})}
            TrashEntry.objects.filter(model_label=f"{label}.post", object_key=str(post.pk)).delete()
            TrashEntry.objects.create(model_label=f"{label}.post", object_key=str(post.pk), title=post.title[:200],
                                      section=section, deleted_at=now, members=members)
            Post.objects.filter(pk=post.pk).update(deleted_at=now)
            Placement.objects.filter(pk__in=places).update(deleted_at=now)


class Migration(migrations.Migration):
    dependencies = [("writing", "0017_clear_old_temp"), ("naver_writing", "0007_post_custom"),
                    ("blog_types", "0019_nunip_site_categories"), ("core", "0002_sourceexclusion_trashentry")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
