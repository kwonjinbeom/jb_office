from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("sync/", views.sync_now, name="sync_now"),
    path("update-code/", views.update_code, name="update_code"),
    path("deploy/webhook/", views.deploy_webhook, name="deploy_webhook"),
    path("settings/", views.app_settings, name="settings"),
    path("api/git/status/", views.api_git_status, name="api_git_status"),
    path("api/git/sync/", views.api_sync, name="api_sync"),
]
