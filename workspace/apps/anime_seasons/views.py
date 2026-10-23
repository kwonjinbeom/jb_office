"""블로그·카페 › memorily 티스토리 › 분기별 애니 추천 및 후기 (2026-10-23 사용자).

글을 쓰기 전에 글감을 모으는 화면. 분기마다 방영작 목록(왼쪽)에서 본 애니를 오른쪽 '본 애니'로 옮기고,
작품을 누르면 맨 오른쪽 칸에 평점(별 반 개 단위)·한 줄 평·감상평을 적는다. 분기가 끝나면 이걸로 추천 글을 쓴다.
주소: ?y=2026&q=3 (보는 분기) · a=<번호> (고른 작품). 목록은 data/<연도>.json 을 migration 으로 넣었다 (0002).
"""
from datetime import date

from django import forms
from django.contrib import messages
from django.db.models import Count, F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import SeasonAnime


class AddForm(forms.ModelForm):
    class Meta:
        model = SeasonAnime
        fields = ["title", "original_title", "aired", "genre", "episodes"]
        widgets = {"aired": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


def _quarter_of(day):
    return (day.month - 1) // 3 + 1


def _url(year, quarter, pk=None):
    return f"{reverse('anime_seasons:index')}?y={year}&q={quarter}" + (f"&a={pk}" if pk else "")


def _int(value, default, lo, hi):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return v if lo <= v <= hi else default


def _default_season():
    """처음 열면: 지금 분기까지 중 목록이 있는 가장 최근 분기 (없으면 지금 분기)."""
    today = timezone.localdate()
    now = (today.year, _quarter_of(today))
    seasons = SeasonAnime.objects.values_list("year", "quarter").distinct().order_by("-year", "-quarter")
    return next((s for s in seasons if s <= now), now)


def index(request):
    year, quarter = _default_season()
    year = _int(request.GET.get("y"), year, 2000, 2100)
    quarter = _int(request.GET.get("q"), quarter if "y" not in request.GET else 1, 1, 4)
    items = SeasonAnime.objects.filter(year=year, quarter=quarter)
    todo = items.filter(watched=False).order_by("aired", "title")
    done = items.filter(watched=True).order_by(F("rating").desc(nulls_last=True), "watched_at", "title")
    counts = dict(SeasonAnime.objects.filter(year=year).values_list("quarter").annotate(n=Count("pk")))
    seen = dict(SeasonAnime.objects.filter(year=year, watched=True).values_list("quarter").annotate(n=Count("pk")))
    picked = items.filter(pk=request.GET.get("a")).first() if request.GET.get("a", "").isdigit() else None
    return render(request, "anime_seasons/index.html", {
        "page_title": "분기별 애니 추천 및 후기", "year": year, "quarter": quarter,
        "quarters": [{"q": q, "n": counts.get(q, 0), "seen": seen.get(q, 0), "url": _url(year, q), "on": q == quarter} for q in range(1, 5)],
        "prev_url": _url(year - 1, quarter), "next_url": _url(year + 1, quarter),
        "todo": todo, "done": done, "picked": picked, "back": _url(year, quarter),
        "add_form": AddForm(),
    })


@require_POST
def move(request, pk):
    """분기 목록 ↔ 본 애니. watched=1 이면 본 애니로."""
    anime = get_object_or_404(SeasonAnime, pk=pk)
    anime.watched = request.POST.get("watched") == "1"
    anime.watched_at = timezone.now() if anime.watched else None
    anime.save(update_fields=["watched", "watched_at", "updated_at"])
    return JsonResponse({"ok": True, "watched": anime.watched})


@require_POST
def save(request, pk):
    """평점·추천·한 줄 평·감상평. 평이나 감상을 적으면 본 애니로 옮긴다."""
    anime = get_object_or_404(SeasonAnime, pk=pk)
    anime.rating = _int(request.POST.get("rating"), None, 1, 10)
    anime.pick = request.POST.get("pick") == "on"
    anime.one_line = request.POST.get("one_line", "").strip()[:120]
    anime.review = request.POST.get("review", "").strip()
    if not anime.watched and (anime.rating or anime.one_line or anime.review):
        anime.watched, anime.watched_at = True, timezone.now()
    anime.save()
    messages.success(request, "감상을 저장했습니다.")
    return redirect(_url(anime.year, anime.quarter, anime.pk))


@require_POST
def add(request):
    """목록에 없는 작품 넣기. 방영 시작일이 있으면 그 분기로, 없으면 보던 분기로."""
    form = AddForm(request.POST)
    year = _int(request.POST.get("year"), timezone.localdate().year, 2000, 2100)
    quarter = _int(request.POST.get("quarter"), 1, 1, 4)
    if not form.is_valid():
        messages.error(request, "제목을 확인하세요.")
        return redirect(_url(year, quarter))
    anime = form.save(commit=False)
    aired = anime.aired
    anime.year, anime.quarter = (aired.year, _quarter_of(aired)) if isinstance(aired, date) else (year, quarter)
    anime.save()
    messages.success(request, f"{anime.title} 을(를) 넣었습니다.")
    return redirect(_url(anime.year, anime.quarter, anime.pk))


@require_POST
def delete(request, pk):
    anime = get_object_or_404(SeasonAnime, pk=pk)
    anime.delete()  # 휴지통으로 (7일간 복원)
    messages.success(request, "작품을 휴지통으로 옮겼습니다.")
    return redirect(_url(anime.year, anime.quarter))
