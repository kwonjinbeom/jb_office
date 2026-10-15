from django.urls import path

from . import views
from .models import Post

app_name = "writing"
urlpatterns = [
    path("", views.post_list, {"stage": Post.Stage.TEMP}, name="list"),
    path("review/", views.post_list, {"stage": Post.Stage.REVIEW}, name="review"),
    path("posts/", views.post_list, {"stage": Post.Stage.POST}, name="posts"),
    path("new/", views.create, name="create"),
    path("move/", views.move, name="move"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/edit/", views.edit, name="edit"),
    path("<int:pk>/status/", views.set_status, name="status"),
    path("<int:pk>/delete/", views.delete, name="delete"),
]
