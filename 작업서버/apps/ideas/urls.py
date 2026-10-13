from django.urls import path

from . import views

app_name = "ideas"

urlpatterns = [
    path("", views.idea_list, name="list"),
    path("new/", views.idea_create, name="create"),
    path("<int:pk>/", views.idea_detail, name="detail"),
    path("<int:pk>/edit/", views.idea_edit, name="edit"),
    path("<int:pk>/delete/", views.idea_delete, name="delete"),
]
