from django.urls import path
from . import views

urlpatterns = [
    path("", views.content_list, name="list"),
    path("new/", views.content_form, name="create"),
    path("folders/new/", views.folder_form, name="folder_create"),
    path("folders/<int:pk>/edit/", views.folder_form, name="folder_edit"),
    path("folders/<int:pk>/delete/", views.delete, {"target": "folder"}, name="folder_delete"),
    path("<int:pk>/", views.content_detail, name="detail"),
    path("<int:pk>/edit/", views.content_form, name="edit"),
    path("<int:pk>/download/", views.download, name="download"),
    path("<int:pk>/delete/", views.delete, name="delete"),
    path("<int:pk>/status/", views.status_update, name="status"),
    path("<int:content_pk>/publications/new/", views.publication_form, name="publication_create"),
    path("<int:content_pk>/publications/<int:pk>/edit/", views.publication_form, name="publication_edit"),
    path("<int:content_pk>/publications/<int:pk>/delete/", views.delete, {"target": "publication"}, name="publication_delete"),
]
