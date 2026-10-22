"""블로그·카페 화면 위쪽 가운데 바로가기 (2026-10-23 사용자): 각 사이트·글쓰기 주소로 바로 가는 작은 버튼.

블로그·카페 아래 메뉴에 들어갔을 때만 보인다 (core.context_processors.navigation → SITE_LINKS, templates/includes/site_links.html).
연필 버튼으로 연 창에서 추가·수정·삭제·순서 바꾸기. 저장하면 보던 화면으로 돌아간다.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import SiteLink


def _back(request):
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else "/")


def _clean(request):
    """이름 · 주소. 주소에 http 가 없으면 https:// 를 붙인다. 틀리면 (None, None)."""
    name = request.POST.get("name", "").strip()[:30]
    url = request.POST.get("url", "").strip()
    if url and "://" not in url:
        url = "https://" + url
    try:
        URLValidator(schemes=["http", "https"])(url)
    except ValidationError:
        messages.warning(request, "주소를 확인하세요. (예: https://blog.naver.com/아이디)")
        return None, None
    if not name:
        messages.warning(request, "이름을 넣으세요.")
        return None, None
    return name, url


@require_POST
def add(request):
    name, url = _clean(request)
    if name:
        top = SiteLink.objects.aggregate(m=Max("order"))["m"]
        SiteLink.objects.create(name=name, url=url, order=0 if top is None else top + 1)
    return _back(request)


@require_POST
def save(request, pk):
    link = get_object_or_404(SiteLink, pk=pk)
    name, url = _clean(request)
    if name:
        link.name, link.url = name, url
        link.save(update_fields=["name", "url"])
    return _back(request)


@require_POST
def delete(request, pk):
    get_object_or_404(SiteLink, pk=pk).delete()
    return _back(request)


@require_POST
def move(request, pk):
    """한 칸 앞(up) · 뒤(down)로. 순서를 0부터 다시 매긴다."""
    links = list(SiteLink.objects.all())
    i = next((n for n, link in enumerate(links) if link.pk == pk), None)
    j = None if i is None else i + (-1 if request.POST.get("dir") == "up" else 1)
    if i is not None and 0 <= j < len(links):
        links[i], links[j] = links[j], links[i]
        for n, link in enumerate(links):
            if link.order != n:
                link.order = n
                link.save(update_fields=["order"])
    return _back(request)
