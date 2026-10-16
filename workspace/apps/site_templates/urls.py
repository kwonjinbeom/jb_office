from django.urls import path

from . import views

app_name = "site_templates"
urlpatterns = [
    path("", views.index, name="index"),
    path("requests.json", views.requests_json, name="requests"),
    path("<int:pk>/", views.site, name="site"),
    path("convert/<int:pk>/", views.convert, name="convert"),
    path("convert/<int:pk>/status/", views.quick_status, name="status"),
]
