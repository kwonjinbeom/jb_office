from django.urls import path

from . import topics, views

app_name = "routines"
urlpatterns = [
    path("", views.index, name="index"),
    path("prompts/", views.prompts, name="prompts"),
    path("ahead/", views.ahead, name="ahead"),
    path("ideas/", views.ideas, name="ideas"),
    path("topics/", topics.page, name="topics"),
    path("topics/run/", topics.run, name="topic_run"),
    path("topics/add/", topics.add, name="topic_add"),
    path("topics/<int:pk>/save/", topics.save, name="topic_save"),
    path("topics/<int:pk>/delete/", topics.delete, name="topic_delete"),
    path("new/", views.edit, name="create"),
    path("doc/<path:rel>", views.doc, name="doc"),
    path("report/<slug:key>/", views.report_api, name="report"),
    path("<int:pk>/count/", views.count, name="count"),
    path("<int:pk>/extra/", views.extra, name="extra"),
    path("<int:pk>/evaluate/", views.evaluate, name="evaluate"),
    path("evaluations/<int:pk>/delete/", views.evaluation_delete, name="evaluation_delete"),
    path("versions/<int:pk>/star/", views.version_star, name="version_star"),
    path("versions/<int:pk>/restore/", views.version_restore, name="version_restore"),
    path("<int:pk>/delete/", views.delete, name="delete"),
    path("<int:pk>/", views.edit, name="edit"),
]
