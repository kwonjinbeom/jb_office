from django.urls import path

from . import views

app_name = "routines"
urlpatterns = [
    path("", views.index, name="index"),
    path("prompts/", views.prompts, name="prompts"),
    path("new/", views.edit, name="create"),
    path("doc/<path:rel>", views.doc, name="doc"),
    path("<int:pk>/count/", views.count, name="count"),
    path("<int:pk>/run/", views.run_local, name="run"),
    path("<int:pk>/delete/", views.delete, name="delete"),
    path("<int:pk>/", views.edit, name="edit"),
]
