from django.urls import path

from . import views

app_name = "anime_seasons"

urlpatterns = [
    path("", views.index, name="index"),
    path("add/", views.add, name="add"),
    path("<int:pk>/move/", views.move, name="move"),
    path("<int:pk>/save/", views.save, name="save"),
    path("<int:pk>/delete/", views.delete, name="delete"),
]
