"""화면을 옮기지 않고 처리하는 요청(목록에서 바로 기록·담기)을 위한 작은 도구.

static/js/app.js 의 form[data-ajax] 가 X-Requested-With: fetch 로 보내면 JSON 으로 답하고,
자바스크립트가 없을 때는 폼의 next(같은 사이트 주소만)로 돌아간다.
"""
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def wants_json(request) -> bool:
    return request.headers.get("X-Requested-With") == "fetch"


def back(request, fallback):
    """폼의 next 가 이 사이트 주소면 그리로, 아니면 fallback 으로."""
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(target)
    return redirect(fallback)


def answer(request, fallback, status=200, **data):
    if wants_json(request):
        return JsonResponse({"ok": status < 400, **data}, status=status)
    return back(request, fallback)
