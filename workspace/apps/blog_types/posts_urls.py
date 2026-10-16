from django.urls import path

from . import posts

app_name = "posts"
urlpatterns = [
    path("", posts.index, name="index"),
    path("bulk/", posts.bulk, name="bulk"),
    path("view/", posts.view, name="view"),
]
