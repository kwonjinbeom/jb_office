from django.urls import path

from . import views

app_name = "blog_types"
urlpatterns = [
    path("", views.index, name="index"),
    path("place/add/", views.place_add, name="place_add"),
    path("place/<int:pk>/status/", views.place_status, name="place_status"),
    path("place/<int:pk>/move/", views.place_move, name="place_move"),
    path("place/<int:pk>/remove/", views.place_remove, name="place_remove"),
    path("<str:kind>/add/", views.add, name="add"),
    path("<str:kind>/<int:pk>/save/", views.save, name="save"),
    path("<str:kind>/<int:pk>/move/", views.move, name="move"),
    path("<str:kind>/<int:pk>/delete/", views.delete, name="delete"),
]
