"""memorily 연재 화면 하나: 왼쪽 회차 목록, 오른쪽 고른 회차 (다룰 것 · 근거 · 상태 · 글로 만들기 · 고치기)."""
from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Episode

SITE = "memorily"
SERIES = "AI 와 블로그 자동화 만들기"
# 연재 방향: memorily 사이트 템플릿(개발자 1인칭 · 겪은 것만)에 맞춘 한 줄씩
DIRECTION = [
    ("독자", "AI 로 일을 자동화해 보고 싶은 개발자·1인 사업자"),
    ("말투", "개발자 1인칭, 겪은 것만 담백하게 (과장·홍보 없이)"),
    ("구성", "겪은 상황 → 해 본 것(코드·화면) → 결과와 느낀 점 → 다음에 해 볼 것"),
    ("제목", f"[{SERIES} EP.N] 한 문장"),
]


class EpisodeForm(forms.ModelForm):
    class Meta:
        model = Episode
        fields = ["number", "title", "hook", "period", "points", "sources"]
        widgets = {"points": forms.Textarea(attrs={"rows": 6}), "sources": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


def post_url(post):
    """글 보기 (그 글의 단계 목록과 함께)"""
    return f"{reverse('posts:view')}?stage={post.stage}&p=tistory:{post.pk}"


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
    counts = {s: sum(1 for e in episodes if e.status == s) for s, _ in Episode.Status.choices}
    for e in episodes:
        e.post_link = post_url(e.post) if e.post else ""
    return render(request, "series/index.html", {
        "page_title": "memorily 연재", "series": SERIES, "direction": DIRECTION,
        "episodes": episodes, "current": None if new else current, "form": form, "new": new,
        "status_choices": Episode.Status.choices, "counts": counts,
    })


@require_POST
def set_status(request, pk):
    ep = get_object_or_404(Episode, pk=pk)
    value = request.POST.get("value", "")
    if value in Episode.Status.values:
        ep.status = value
        ep.save(update_fields=["status", "updated_at"])
    return redirect(f"{reverse('series:index')}?ep={ep.pk}")


def _skeleton(ep):
    """memorily 구성대로 비어 있는 뼈대. 다룰 것은 '해 본 것' 아래 메모로, 근거는 끝에."""
    points = "\n".join(f"- {p}" for p in ep.point_list) or "- "
    sources = "\n".join(f"- {s}" for s in ep.source_list)
    parts = [
        f"## 겪은 상황\n{ep.hook}",
        f"## 해 본 것\n{points}\n\n[그림] 그때 화면이나 코드",
        "## 결과와 느낀 점\n",
        "## 다음에 해 볼 것\n",
    ]
    if sources:
        parts.append(f"참고 (근거):\n{sources}")
    return "\n\n".join(parts)


@require_POST
def make_post(request, pk):
    """회차 → memorily 임시글 (이미 있으면 그 글로)."""
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
    return redirect(post_url(ep.post))
