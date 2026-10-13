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
        "role": settings.ROLE,
        "is_server": settings.IS_SERVER,
        "pull_enabled": settings.DEPLOY["PULL_ENABLED"],
    }
    return render(request, "core/home.html", context)


@require_POST
def update_code(request):
    """서버 역할 전용: GitHub 에서 최신 코드를 받고 앱을 재시작한다."""
    if not settings.DEPLOY["PULL_ENABLED"]:
        messages.error(request, "이 서버에서는 코드 갱신이 꺼져 있습니다 (DEPLOY_PULL_ENABLED).")
        return redirect("core:home")
    result = gitstate.pull_and_reload()
    if result["ok"]:
        pull_out = next((s["output"] for s in result["steps"] if s["name"] == "pull"), "")
        pull_tail = pull_out.splitlines()[-1] if pull_out else ""
        mig_out = next((s["output"] for s in result["steps"] if s["name"] == "migrate"), "")
        applied = sum(1 for line in mig_out.splitlines() if "Applying" in line)
        summary = f"pull 완료 ({pull_tail}). migrate {applied}건 적용. 정적 파일 수집 완료."
        if result["reloaded"]:
            messages.success(request, f"{summary} 앱 재시작을 요청했습니다. 몇 초 뒤 새로고침하세요.")
        else:
            messages.success(request, f"{summary} 재시작 파일이 설정되지 않아 Web 탭에서 Reload 가 필요합니다.")
    else:
        failed = next((s for s in result["steps"] if not s["ok"]), None)
        detail = (failed["output"][-400:] if failed else "")
        messages.error(request, f"코드 갱신 실패: {result.get('error')} {detail}")
    return redirect("core:home")


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
