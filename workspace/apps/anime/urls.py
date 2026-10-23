from django.urls import path

from . import views

app_name = "anime"

urlpatterns = [
    path("", views.index, name="index"),
    path("titles/add/", views.add, name="add"),
    path("titles/<int:pk>/pick/", views.pick, name="pick"),
    path("titles/<int:pk>/status/", views.status, name="status"),
    path("titles/<int:pk>/delete/", views.delete, name="delete"),
]
