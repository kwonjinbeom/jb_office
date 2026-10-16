from django.urls import path

from . import views

app_name = "blog_ops"
urlpatterns = [
    path("", views.index, name="index"),
    path("plans/add/", views.plan_add, name="plan_add"),
    path("plans/<int:pk>/", views.plan_edit, name="plan_edit"),
    path("plans/<int:pk>/status/", views.plan_status, name="plan_status"),
    path("plans/<int:pk>/delete/", views.plan_delete, name="plan_delete"),
    path("sync/", views.sync, name="sync"),
]
