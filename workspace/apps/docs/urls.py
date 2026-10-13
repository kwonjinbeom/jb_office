from django.urls import path

from . import views

app_name = "docs"

urlpatterns = [
    path("", views.doc_list, name="list"),
    path("view/<path:slug>", views.doc_detail, name="detail"),
]
