"""블로그·카페 › memorily 티스토리 › 애니 총정리 (2026-10-21 사용자).

나루토처럼 애니↔만화 환산기 글을 작품마다 더 쓰기 위한 md 를 보여 준다.
폴더 settings.ANIME_DIR: 00_작업순서.md (모든 작품 공통) + 작품마다 md 하나. 작품 md 의 `상태:` 줄을 목록에 보인다.
md 는 Claude 가 저장소에서 고치고 main 에 올린다 — 서버는 git pull 로 같은 파일을 읽는다.

2026-10-23 사용자: 맨 왼쪽에 전체 애니 목록(AnimeTitle, 유명한 순)을 두고 담기·빼기·삭제·상태를 고친다.
가운데 '작업 순서 · 작품'에는 공통 md + 담은 작품만 나온다 (md 가 있으면 doc_key 로 잇는다).
주소: ?d=<md 이름> (md 보기) · a=<번호> (md 가 아직 없는 담은 작품).

2026-10-23 사용자: '글쓰기·변환' — 원고 없는 담은 작품(대기·작업 중)을 PC 터미널 claude 가 글쓰기부터 변환까지 (run.py).
2026-10-27 사용자: 작품 2개를 담고 눌렀는데 PC 창이 "클립보드에 애니 총정리 안내문이 없습니다"로 꺼졌다.
→ 안내문을 서버에도 잠깐 두고(BRIEF_KEY), PC 가 클립보드에서 못 찾으면 링크의 key 로 brief 에서 받아 간다.
"""
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path

import markdown
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db.models import Max
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting

from . import run as anime_run
from .models import AnimeTitle

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists"]
STATUS_KEYS = {key for key, _ in AnimeTitle.STATUS}
TO_WRITE = ("todo", "doing")  # '글쓰기·변환' 대상: 담은 작품 중 원고가 아직 없는 것
FOLDER = re.compile(r"T\d+_[^/\\.]+")  # 원고 폴더 (경로 문자·점 없이)
DOC = re.compile(r"\d{2}_[^/\\.]+")  # 애니총정리 작품 md 이름
BRIEF_KEY = "anime_brief"  # 마지막 '글쓰기·변환' 안내문 {key, prompt, at} (PC 가 한 번 받아 가면 지운다)
BRIEF_TTL = timedelta(minutes=30)


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
        "to_write": [w["anime"] for w in works if w["anime"] and w["anime"].status in TO_WRITE],
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


@require_POST
def write_run(request):
    """'글쓰기·변환': 원고 없는 담은 작품의 안내문을 돌려준다 (JSON). 화면이 복사해 jbroutine:anime 링크로 PC 터미널을 연다."""
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    if not token:
        return JsonResponse({"error": "설정 화면에서 보고 토큰을 먼저 만드세요. claude 가 글을 서버로 넣을 때 씁니다."}, status=400)
    works = _works(_docs(), list(AnimeTitle.objects.all()))
    titles = [w["anime"] for w in works if w["anime"] and w["anime"].status in TO_WRITE]
    if not titles:
        return JsonResponse({"error": "원고 없는 담은 작품이 없습니다. 왼쪽 목록에서 담으세요."}, status=400)
    for a in titles:
        if a.status != "doing":
            a.status = "doing"
            a.save(update_fields=["status", "updated_at"])
    now = timezone.localtime()
    prompt, key = anime_run.launcher(request, titles, token), f"an-{secrets.token_hex(10)}"  # key 는 brief 를 받는 열쇠라 짐작 못 하게
    AppSetting.set(BRIEF_KEY, json.dumps({"key": key, "prompt": prompt, "at": now.isoformat()}, ensure_ascii=False))
    return JsonResponse({"prompt": prompt, "key": key, "day": now.date().isoformat(), "count": len(titles)})


@login_not_required
def brief(request, key):
    """PC 실행기(routines/local_run)가 클립보드에서 안내문을 못 찾았을 때 받아 간다. 링크의 key 가 맞고 30분 안이면 한 번만."""
    try:
        saved = json.loads(AppSetting.get(BRIEF_KEY) or "{}")
        fresh = timezone.now() - datetime.fromisoformat(saved["at"]) < BRIEF_TTL
    except (ValueError, KeyError):
        saved, fresh = {}, False
    if not fresh or not hmac.compare_digest(key, saved.get("key", "")):
        return HttpResponse("안내문 없음 (30분이 지났거나 다시 눌렀습니다)", status=404)
    AppSetting.objects.filter(key=BRIEF_KEY).delete()
    return HttpResponse(saved["prompt"], content_type="text/plain; charset=utf-8")


@csrf_exempt
@login_not_required
@require_POST
def api_place(request, pk):
    """PC 터미널 claude 가 원고를 main 에 올린 뒤 부른다: folder(원고 폴더) · doc(작품 md 이름).
    서버에 받은 원고를 발행예정글 + memorily › 애니 매핑 + 변환 완료로 넣고, 애니를 '원고 완료'로 바꿔 md 와 잇는다."""
    from apps.site_templates.views import _form_fields  # Windows curl 의 한글(cp949) 칸도 읽는다
    from apps.writing.place_drafts import place
    from django.apps import apps

    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    if not token or not hmac.compare_digest(request.GET.get("token", ""), token):
        return HttpResponseForbidden("token")
    anime = get_object_or_404(AnimeTitle, pk=pk)
    data = _form_fields(request)
    folder, doc = data.get("folder", "").strip(), data.get("doc", "").strip().removesuffix(".md")
    if not FOLDER.fullmatch(folder) or (doc and not DOC.fullmatch(doc)):
        return HttpResponseBadRequest("folder 는 T번호_이름, doc 은 두자리번호_이름 이어야 합니다")
    if not place(apps, folder):
        return HttpResponse("원고 없음 (서버가 아직 push 를 받기 전이거나 폴더 이름이 다릅니다)", status=404)
    anime.status = "written"
    if doc:
        anime.doc_key = doc
    anime.picked = True
    anime.save(update_fields=["status", "doc_key", "picked", "updated_at"])
    return HttpResponse(f"ok {anime.title} → 발행예정글 · memorily › 애니 변환 완료")
