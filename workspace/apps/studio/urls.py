from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("", views.index, name="index"),
    path("cartoon/", views.cartoon, name="cartoon"),
    path("shorts/", views.shorts, name="shorts"),
    path("thread/", views.thread, name="thread"),
    path("prompts/", views.prompts, name="prompts"),
    path("review/", views.review, name="review"),
]
