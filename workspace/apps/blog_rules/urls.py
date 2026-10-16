from django.urls import path

from . import views

app_name = "blog_rules"
urlpatterns = [
    path("", views.index, name="index"),
    path("blogs/new/", views.blog_form, name="blog_create"),
    path("blogs/<int:pk>/", views.blog_form, name="blog_edit"),
    path("count/", views.count, name="count"),
    path("rules/add/", views.rule_add, name="rule_add"),
    path("rules/<int:pk>/", views.rule_form, name="rule_edit"),
    path("<str:kind>/<int:pk>/delete/", views.delete, name="delete"),
]
