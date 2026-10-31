from django.urls import path

from . import followups, topics, views

app_name = "routines"
urlpatterns = [
    path("", views.index, name="index"),
    path("prompts/", views.prompts, name="prompts"),
    path("ahead/", views.ahead, name="ahead"),
    path("followups/", followups.page, name="followups"),
    path("followups/add/", followups.add, name="followup_add"),
    path("followups/new/", followups.api_new, name="followup_new"),
    path("followups/<int:pk>/save/", followups.save, name="followup_save"),
    path("followups/<int:pk>/resume/", followups.resume, name="followup_resume"),
    path("followups/<int:pk>/report/", followups.api_report, name="followup_report"),
    path("followups/<int:pk>/<str:action>/", followups.mark, name="followup_mark"),
    path("followups/runs/<int:pk>/promote/", followups.promote, name="followup_promote"),
    path("followups/runs/<int:pk>/close/", followups.close_run, name="followup_close_run"),
    path("ideas/", views.ideas, name="ideas"),
    path("update/", views.update, name="update"),
    path("convert/<str:day>/", views.convert_api, name="convert"),
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
