from django.urls import path

from . import views

app_name = "schedule"

urlpatterns = [
    path("", views.index, name="index"),
    path("save/", views.save, name="save"),
    path("<int:pk>/done/", views.toggle_done, name="done"),
    path("<int:pk>/delete/", views.delete, name="delete"),
]
