from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.evidence.models import Evidence
from apps.ideas.models import Idea, IdeaLog
from apps.tasks.models import Task

from . import autosync, gitstate
from .menus import get_menus


def home(request):
    today = timezone.localdate()

    # 진행 중인 아이디어: 실험군·진행중·검토중. 현재 단계와 열린 할 일 수를 함께 보여 준다.
    active_ideas = list(
        Idea.objects.filter(status__in=[Idea.Status.EXPERIMENT, Idea.Status.ACTIVE, Idea.Status.REVIEW])
        .order_by("-priority", "code")
        .prefetch_related("stages")
    )
    open_tasks = list(Task.objects.filter(done=False).select_related("idea", "stage"))
    open_by_idea: dict[int, int] = {}
    for t in open_tasks:
        if t.idea_id:
            open_by_idea[t.idea_id] = open_by_idea.get(t.idea_id, 0) + 1
    for idea in active_ideas:
        idea.open_task_count = open_by_idea.get(idea.pk, 0)

    overdue = [t for t in open_tasks if t.due and t.due < today]
    today_tasks = [t for t in open_tasks if t.due == today]
    undated = [t for t in open_tasks if not t.due][:8]

    status = gitstate.get_status()
    state = gitstate.load_state()
    context = {
        "page_title": "홈",
        "menus": get_menus(),
        "active_ideas": active_ideas,
        "overdue": overdue,
        "today_tasks": today_tasks,
        "undated": undated,
        "open_count": len(open_tasks),
        "recent_logs": IdeaLog.objects.select_related("idea", "stage")[:8],
        "recent_links": Evidence.objects.select_related("idea")[:6],
        "git": status,
        "last_sync": state.get("last"),
        "autosync_running": autosync.is_running(),
        "autosync_interval": settings.AUTOSYNC["INTERVAL_SECONDS"],
        "role": settings.ROLE,
        "is_server": settings.IS_SERVER,
        "pull_enabled": settings.DEPLOY["PULL_ENABLED"],
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


@require_POST
def update_code(request):
    """서버 역할 전용: GitHub 에서 최신 코드를 받고 migrate·collectstatic 후 앱을 재시작한다."""
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
        detail = failed["output"][-400:] if failed else ""
        messages.error(request, f"코드 갱신 실패: {result.get('error')} {detail}")
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
