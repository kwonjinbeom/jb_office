from django.urls import path

from . import views

app_name = "evidence"

urlpatterns = [
    path("", views.evidence_list, name="list"),
    path("new/", views.create, name="create"),
    path("<int:pk>/edit/", views.edit, name="edit"),
    path("<int:pk>/delete/", views.delete, name="delete"),
]
