from django.urls import path

from . import views

app_name = "blog_types"
urlpatterns = [
    path("", views.index, name="index"),
    path("<str:kind>/add/", views.add, name="add"),
    path("<str:kind>/<int:pk>/save/", views.save, name="save"),
    path("<str:kind>/<int:pk>/move/", views.move, name="move"),
    path("<str:kind>/<int:pk>/delete/", views.delete, name="delete"),
]
