from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("sync/", views.sync_now, name="sync_now"),
    path("api/git/status/", views.api_git_status, name="api_git_status"),
    path("api/git/sync/", views.api_sync, name="api_sync"),
]
