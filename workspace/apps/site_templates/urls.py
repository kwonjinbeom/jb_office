from django.urls import path

from . import views

app_name = "site_templates"
urlpatterns = [
    path("", views.index, name="index"),
    path("requests.json", views.requests_json, name="requests"),
    path("run/", views.run, name="run"),
    path("reconvert/", views.reconvert, name="reconvert"),
    path("panel/", views.panel, name="panel"),
    path("post/", views.post_page, name="post"),
    path("api/convert/<int:pk>/", views.api_save, name="api_save"),
    path("api/state/", views.api_state, name="api_state"),
    path("api/posts/", views.api_posts, name="api_posts"),
    path("api/place/", views.api_place, name="api_place"),
    path("api/stage/", views.api_stage, name="api_stage"),
    path("<int:pk>/", views.site, name="site"),
    path("convert/<int:pk>/", views.convert, name="convert"),
]
