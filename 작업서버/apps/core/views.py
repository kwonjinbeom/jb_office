from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from . import autosync, gitstate
from .menus import get_menus


def home(request):
    status = gitstate.get_status()
    state = gitstate.load_state()
    context = {
        "page_title": "홈",
        "menus": get_menus(),
        "git": status,
        "last_sync": state.get("last"),
        "sync_history": state.get("history", [])[:8],
        "autosync_running": autosync.is_running(),
        "autosync_interval": settings.AUTOSYNC["INTERVAL_SECONDS"],
    }
    return render(request, "core/home.html", context)


@require_POST
def sync_now(request):
    result = gitstate.run_sync(reason="manual", message=request.POST.get("message") or None)
    if result["ok"]:
        if result["committed"]:
            messages.success(request, f"동기화 완료: {result['message']}")
        else:
            messages.info(request, "변경 사항이 없어 커밋 없이 pull/push 만 확인했습니다.")
    else:
        messages.error(request, f"동기화 실패: {result.get('error')}")
    return redirect("core:home")


@require_GET
def api_git_status(request):
    fetch = request.GET.get("fetch") == "1"
    data = gitstate.get_status(fetch=fetch)
    data["last_sync"] = gitstate.load_state().get("last")
    data["autosync_running"] = autosync.is_running()
    return JsonResponse(data)


@require_POST
def api_sync(request):
    result = gitstate.run_sync(reason="manual-api")
    return JsonResponse(result, status=200 if result["ok"] else 500)
