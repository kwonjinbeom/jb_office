"""블로그·카페 › memorily 티스토리 › 애니 총정리 (2026-10-21 사용자).

나루토처럼 애니↔만화 환산기 글을 작품마다 더 쓰기 위한 md 를 보여 준다.
폴더 settings.ANIME_DIR: 00_작업순서.md (모든 작품 공통) + 작품마다 md 하나. 작품 md 의 `상태:` 줄을 목록에 보인다.
md 는 Claude 가 저장소에서 고치고 main 에 올린다 — 서버는 git pull 로 같은 파일을 읽는다.

2026-10-23 사용자: 맨 왼쪽에 전체 애니 목록(AnimeTitle, 유명한 순)을 두고 담기·빼기·삭제·상태를 고친다.
가운데 '작업 순서 · 작품'에는 공통 md + 담은 작품만 나온다 (md 가 있으면 doc_key 로 잇는다).
주소: ?d=<md 이름> (md 보기) · a=<번호> (md 가 아직 없는 담은 작품).
"""
import re
from pathlib import Path

import markdown
from django.conf import settings
from django.contrib import messages
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import AnimeTitle

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists"]
STATUS_KEYS = {key for key, _ in AnimeTitle.STATUS}


def _docs():
    root = Path(settings.ANIME_DIR)
    if not root.is_dir():
        return []
    out = []
    for f in sorted(root.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        title = re.search(r"^#\s+(.+)$", text, re.M)
        status = re.search(r"^상태:\s*(.+)$", text, re.M)
        out.append({"key": f.stem, "title": title.group(1).strip() if title else f.stem,
                    "status": status.group(1).strip() if status else "", "text": text,
                    "guide": f.stem.startswith("00")})
    return out


def _works(docs, titles):
    """가운데 칸: 공통 md → 담은 작품 (md 가 있는 것은 md 순서대로, 없는 것은 목록 순서대로).
    어느 애니에도 이어지지 않은 작품 md 는 잃지 않게 끝에 그대로 둔다."""
    by_key = {d["key"]: d for d in docs}
    linked = {t.doc_key for t in titles if t.doc_key}
    picked = [t for t in titles if t.picked]
    picked.sort(key=lambda t: (0, t.doc_key) if t.doc_key in by_key else (1, f"{t.order:08d}"))
    works = [{"doc": d, "anime": None, "key": d["key"]} for d in docs if d["guide"]]
    works += [{"doc": by_key.get(t.doc_key), "anime": t, "key": t.doc_key if t.doc_key in by_key else f"a{t.pk}"} for t in picked]
    works += [{"doc": d, "anime": None, "key": d["key"]} for d in docs if not d["guide"] and d["key"] not in linked]
    return works


def index(request):
    docs = _docs()
    titles = list(AnimeTitle.objects.all())
    works = _works(docs, titles)
    want = request.GET.get("d") or (f"a{request.GET['a']}" if request.GET.get("a") else "")
    current = next((w for w in works if w["key"] == want), works[0] if works else None)
    doc = current and current["doc"]
    html = markdown.markdown(doc["text"], extensions=MD_EXTENSIONS) if doc else ""
    return render(request, "anime/index.html", {
        "page_title": "애니 총정리", "titles": titles, "works": works, "current": current, "html": html,
        "work_count": sum(1 for w in works if w["anime"] or not w["doc"]["guide"]),
        "statuses": AnimeTitle.STATUS, "here": request.get_full_path(),
    })


def _back(request):
    nxt = request.POST.get("next", "")
    return nxt if url_has_allowed_host_and_scheme(nxt, {request.get_host()}) else reverse("anime:index")


@require_POST
def add(request):
    title = request.POST.get("title", "").strip()[:120]
    if not title:
        messages.error(request, "제목을 넣으세요.")
    elif AnimeTitle.objects.filter(title=title).exists():
        messages.error(request, f"{title} 은(는) 이미 목록에 있습니다.")
    else:
        last = AnimeTitle.objects.aggregate(m=Max("order"))["m"] or 0
        AnimeTitle.objects.create(title=title, order=last + 10)
        messages.success(request, f"{title} 을(를) 목록에 넣었습니다.")
    return redirect(_back(request))


@require_POST
def pick(request, pk):
    """담기(picked=1) · 빼기(picked=0). 빼도 상태·md 연결은 남는다."""
    anime = get_object_or_404(AnimeTitle, pk=pk)
    anime.picked = request.POST.get("picked") == "1"
    anime.save(update_fields=["picked", "updated_at"])
    messages.success(request, f"{anime.title} 을(를) {'담았습니다' if anime.picked else '뺐습니다'}.")
    return redirect(_back(request))


@require_POST
def status(request, pk):
    anime = get_object_or_404(AnimeTitle, pk=pk)
    if request.POST.get("status") in STATUS_KEYS:
        anime.status = request.POST["status"]
        anime.save(update_fields=["status", "updated_at"])
    return redirect(_back(request))


@require_POST
def delete(request, pk):
    anime = get_object_or_404(AnimeTitle, pk=pk)
    anime.delete()  # 휴지통으로 (7일간 복원)
    messages.success(request, f"{anime.title} 을(를) 휴지통으로 옮겼습니다.")
    return redirect(_back(request))
