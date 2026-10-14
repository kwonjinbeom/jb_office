from django.urls import path
from . import views

app_name = "discussions"
urlpatterns = [
    path("", views.discussion_list, name="list"),
    path("new/", views.discussion_form, name="create"),
    path("<int:pk>/", views.discussion_detail, name="detail"),
    path("<int:pk>/edit/", views.discussion_form, name="edit"),
    path("<int:pk>/quick/", views.quick_update, name="quick"),
    path("<int:pk>/delete/", views.discussion_delete, name="delete"),
    path("files/<path:rel>", views.asset, name="asset"),
]
