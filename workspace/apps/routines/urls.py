from django.urls import path

from . import views

app_name = "routines"
urlpatterns = [
    path("", views.index, name="index"),
    path("<int:pk>/count/", views.count, name="count"),
    path("<int:pk>/run/", views.run_local, name="run"),
    path("<int:pk>/", views.edit, name="edit"),
]
