from django.urls import path

from . import links, views

app_name = "blog_types"
urlpatterns = [
    path("", views.index, name="index"),
    # 위쪽 바로가기 (2026-10-23 사용자). '<str:kind>/add/' 보다 먼저 둔다
    path("links/add/", links.add, name="link_add"),
    path("links/<int:pk>/save/", links.save, name="link_save"),
    path("links/<int:pk>/delete/", links.delete, name="link_delete"),
    path("links/<int:pk>/move/", links.move, name="link_move"),
    path("place/add/", views.place_add, name="place_add"),
    path("place/<int:pk>/status/", views.place_status, name="place_status"),
    path("place/<int:pk>/move/", views.place_move, name="place_move"),
    path("place/<int:pk>/remove/", views.place_remove, name="place_remove"),
    path("<str:kind>/add/", views.add, name="add"),
    path("<str:kind>/<int:pk>/save/", views.save, name="save"),
    path("<str:kind>/<int:pk>/move/", views.move, name="move"),
    path("<str:kind>/<int:pk>/delete/", views.delete, name="delete"),
]
