"""memorily 연재 화면 하나: 왼쪽 회차 목록(화면별), 오른쪽 고른 회차 (흐름 · 근거 · 상태 · 글로 만들기 · 고치기)."""
from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Episode

SITE = "memorily"
SERIES = "AI 와 블로그 자동화 만들기"
# 연재 방향 (2026-10-20 사용자): 필요한 화면을 하나씩 더하고 바꾸고 메우며 체계가 잡혀 가는 모습. memorily 템플릿(개발자 1인칭)
DIRECTION = [
    ("보여줄 것", "첫 화면부터 필요한 화면을 하나씩 더하고, 써 보며 바꾸고, 프롬프트를 다듬고, 부족한 점을 메워 체계가 잡혀 가는 과정"),
    ("구성", "필요했던 것 → 처음 만든 것 → 써 보니 부족했던 점 → 이렇게 바꿨다 → 지금 모습"),
    ("말투", "개발자 1인칭, 겪은 것만 담백하게 · 화면 캡처 전/후"),
    ("제목", f"[{SERIES} EP.N] 화면 이름 + 한 문장"),
]


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


SECTIONS = [  # (소제목, 그 아래 갈 흐름 말머리, 사진 자리)
    ("처음 만든 것", ("처음",), "[사진] 처음 화면"),
    ("써 보니 부족했던 점", ("부족",), ""),
    ("이렇게 바꿨다", ("바꿈", "메움", "나눔", "합침", "넓힘", "정리", "고침", "다듬음", ""), "[사진] 바꾼 뒤 화면"),
    ("지금 모습", ("지금",), ""),
]


def _skeleton(ep):
    """연재 구성대로 뼈대: 필요했던 것 → 처음 만든 것 → 써 보니 부족했던 점 → 이렇게 바꿨다 → 지금 모습. 흐름 줄은 말머리대로 나눠 넣는다."""
    parts = [f"## 필요했던 것\n{ep.hook}"]
    for head, words, photo in SECTIONS:
        lines = "\n".join(f"- {text}" for word, text in ep.steps if word in words)
        parts.append("\n\n".join(x for x in (f"## {head}", lines or "- ", photo) if x))
    sources = "\n".join(f"- {s}" for s in ep.source_list)
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
