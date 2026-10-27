from django.urls import path

from . import views

app_name = "blog_ops"
urlpatterns = [
    path("", views.index, name="index"),
    path("check/", views.check, name="check"),
    path("status/", views.status, name="status"),
    path("api/feeds/", views.api_feeds, name="api_feeds"),
    path("stats/", views.stats_page, name="stats"),
]
