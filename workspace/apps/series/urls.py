from django.urls import path

from . import views

app_name = "series"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:pk>/status/", views.set_status, name="status"),
    path("<int:pk>/post/", views.make_post, name="make_post"),
    path("shot/<int:number>/<str:name>", views.shot, name="shot"),
]
