from django.urls import path

from . import views

app_name = "daily_ideas"

urlpatterns = [
    path("", views.daily_list, name="list"),
    path("<str:item_id>/adopt/", views.adopt, name="adopt"),
]
