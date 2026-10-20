"""블로그·카페 › memorily 연재: 세 칸 (2026-10-20 사용자).
왼쪽 회차 목록(글 보기 왼쪽 목록과 같은 크기) · 가운데 고른 회차 요약(흐름 · 화면 · 근거 · 상태 · 내 추가 설명) ·
오른쪽 글쓰기(버튼, 만든 뒤에는 그 글)."""
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Episode

SITE = "memorily"
SERIES = "AI 와 블로그 자동화 만들기"
# 연재 방향: 필요한 화면을 하나씩 더하고 바꾸고 메우며 체계가 잡혀 가는 모습. memorily 템플릿(개발자 1인칭).
# 글 구성: 필요했던 것 → 처음 만든 것 → 써 보니 부족했던 점 → 이렇게 바꿨다 → 지금 모습 (_skeleton)


class EpisodeForm(forms.ModelForm):
    class Meta:
        model = Episode
        fields = ["number", "title", "screen", "period", "hook", "points", "sources"]
        widgets = {"points": forms.Textarea(attrs={"rows": 7}), "sources": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


def post_url(post):
    """글 보기 (그 글의 단계 목록과 함께)"""
    return f"{reverse('posts:view')}?stage={post.stage}&p=tistory:{post.pk}"


IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def shots(number):
    """회차 사진: SERIES_SHOTS_DIR/EP01/<순서>_<말머리>_<설명>.jpg (2026-10-20).
    말머리 '그때' = 그날 화면을 확인하며 찍은 원본, 그 밖(처음·바꿈·지금 …) = 그 시점 코드를 다시 띄워 찍은 것."""
    folder = Path(settings.SERIES_SHOTS_DIR) / f"EP{number:02d}"
    if not folder.is_dir():
        return []
    out = []
    for p in sorted(folder.iterdir(), key=lambda p: p.name):
        if p.suffix.lower() not in IMAGE_EXT:
            continue
        _, _, rest = p.stem.partition("_")
        word, _, label = rest.partition("_")
        out.append({"name": p.name, "word": word, "label": label or word, "original": word == "그때",
                    "url": reverse("series:shot", args=[number, p.name]), "path": f"EP{number:02d}/{p.name}"})
    return out


def shot(request, number, name):
    """회차 사진 한 장 (목록에 있는 파일만)."""
    item = next((s for s in shots(number) if s["name"] == name), None)
    if item is None:
        raise Http404
    return FileResponse(open(Path(settings.SERIES_SHOTS_DIR) / f"EP{number:02d}" / name, "rb"))


def index(request):
    request.nav_key = "series"
    episodes = list(Episode.objects.select_related("post"))
    pick = request.GET.get("ep", "")
    current = next((e for e in episodes if str(e.pk) == pick), episodes[0] if episodes else None)
    new = request.GET.get("new") == "1"
    editing = new or (current is not None and request.GET.get("edit") == "1")
    form = None
    if editing:
        instance = None if new else current
        initial = {"number": (episodes[-1].number + 1) if episodes else 1} if new else None
        form = EpisodeForm(request.POST or None, instance=instance, initial=initial)
        if request.method == "POST" and form.is_valid():
            ep = form.save()
            messages.success(request, f"EP.{ep.number} 을(를) 저장했습니다.")
            return redirect(f"{reverse('series:index')}?ep={ep.pk}")
    for e in episodes:
        e.post_link = post_url(e.post) if e.post else ""
    post_html = ""
    if current is not None and current.post is not None and not new:
        from apps.writing.render import render_body
        post_html = render_body(current.post.body)
    return render(request, "series/index.html", {
        "page_title": "memorily 연재", "series": SERIES,
        "episodes": episodes, "current": None if new else current, "form": form, "new": new,
        "status_choices": Episode.Status.choices,
        "shots": shots(current.number) if current and not new else [],
        "post_html": post_html,
    })


@require_POST
def set_note(request, pk):
    """가운데 요약의 '내 추가 설명' 저장. 글쓰기 때 '필요했던 것' 아래에 들어간다."""
    ep = get_object_or_404(Episode, pk=pk)
    ep.note = request.POST.get("note", "").replace("\r\n", "\n").strip()
    ep.save(update_fields=["note", "updated_at"])
    messages.success(request, f"EP.{ep.number} 추가 설명을 저장했습니다.")
    return redirect(f"{reverse('series:index')}?ep={ep.pk}")


@require_POST
def set_status(request, pk):
    ep = get_object_or_404(Episode, pk=pk)
    value = request.POST.get("value", "")
    if value in Episode.Status.values:
        ep.status = value
        ep.save(update_fields=["status", "updated_at"])
    return redirect(f"{reverse('series:index')}?ep={ep.pk}")


SECTIONS = [  # (소제목, 그 아래 갈 흐름·사진 말머리, 사진이 없을 때 자리)
    ("처음 만든 것", ("처음",), "[사진] 처음 화면"),
    ("써 보니 부족했던 점", ("부족",), ""),
    ("이렇게 바꿨다", ("바꿈", "메움", "나눔", "합침", "넓힘", "정리", "고침", "다듬음", "그때", ""), "[사진] 바꾼 뒤 화면"),
    ("지금 모습", ("지금",), ""),
]


def _skeleton(ep):
    """연재 구성대로 뼈대: 필요했던 것 → 처음 만든 것 → 써 보니 부족했던 점 → 이렇게 바꿨다 → 지금 모습.
    흐름 줄과 회차 사진은 말머리대로 나눠 넣는다 (사진은 '[사진] 설명 — EP01/파일' 한 줄, 블로그에 직접 올린다)."""
    parts = ["## 필요했던 것\n" + "\n\n".join(x for x in (ep.hook, ep.note) if x)]  # 내 추가 설명은 내 말 그대로
    photos = shots(ep.number)
    for head, words, placeholder in SECTIONS:
        lines = "\n".join(f"- {text}" for word, text in ep.steps if word in words)
        pics = "\n".join(f"[사진] {s['label']} — {s['path']}" for s in photos if s["word"] in words)
        parts.append("\n\n".join(x for x in (f"## {head}", lines or "- ", pics or placeholder) if x))
    sources = "\n".join(f"- {s}" for s in ep.source_list)
    if sources:
        parts.append(f"참고 (근거):\n{sources}")
    return "\n\n".join(parts)


@require_POST
def make_post(request, pk):
    """회차 → memorily 임시글 (이미 있으면 그대로). 만든 글은 이 화면 오른쪽에 보인다."""
    from apps.writing.models import Post
    ep = get_object_or_404(Episode, pk=pk)
    if ep.post_id is None:
        ep.post = Post.objects.create(
            title=f"[{SERIES} EP.{ep.number}] {ep.title}", summary=ep.hook[:300], body=_skeleton(ep),
            target=SITE, tags="AI, 자동화, Claude, 블로그 자동화",
        )
        if ep.status == Episode.Status.PLAN:
            ep.status = Episode.Status.WRITING
        ep.save()
        messages.success(request, f"EP.{ep.number} 을(를) memorily 임시글로 만들었습니다.")
    return redirect(f"{reverse('series:index')}?ep={ep.pk}")
