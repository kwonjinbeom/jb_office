from django.urls import path

from . import posts

app_name = "posts"
urlpatterns = [
    path("", posts.index, name="index"),
    path("bulk/", posts.bulk, name="bulk"),
    path("promote/", posts.promote, name="promote"),
    path("site/", posts.site, name="site"),
    path("plan/", posts.plan, name="plan"),
    path("view/", posts.view, name="view"),
    path("planned/", posts.planned, name="planned"),
    path("published/", posts.published, name="published"),
]
