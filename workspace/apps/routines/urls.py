from django.urls import path

from . import views

app_name = "routines"
urlpatterns = [
    path("", views.index, name="index"),
    path("prompts/", views.prompts, name="prompts"),
    path("new/", views.edit, name="create"),
    path("doc/<path:rel>", views.doc, name="doc"),
    path("<int:pk>/count/", views.count, name="count"),
    path("<int:pk>/picks/", views.picks, name="picks"),
    path("<int:pk>/evaluate/", views.evaluate, name="evaluate"),
    path("evaluations/<int:pk>/delete/", views.evaluation_delete, name="evaluation_delete"),
    path("versions/<int:pk>/star/", views.version_star, name="version_star"),
    path("versions/<int:pk>/restore/", views.version_restore, name="version_restore"),
    path("<int:pk>/delete/", views.delete, name="delete"),
    path("<int:pk>/", views.edit, name="edit"),
]
