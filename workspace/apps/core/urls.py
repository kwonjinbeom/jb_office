from django.urls import path

from . import views, trash_views

app_name = "core"

urlpatterns = [
    path("trash/", trash_views.index, name="trash"),
    path("trash/preview/", trash_views.preview, name="trash_preview"),
    path("trash/move/", trash_views.move, name="trash_move"),
    path("trash/restore/", trash_views.restore_items, name="trash_restore"),
    path("", views.home, name="home"),
    path("sync/", views.sync_now, name="sync_now"),
    path("update-code/", views.update_code, name="update_code"),
    path("deploy/webhook/", views.deploy_webhook, name="deploy_webhook"),
    path("settings/", views.app_settings, name="settings"),
    path("api/git/status/", views.api_git_status, name="api_git_status"),
]
