from django.urls import path
from . import views

app_name = "writing"
urlpatterns = [
    path("", views.draft_list, name="list"),
    path("new/", views.create, name="create"),
    path("import/", views.import_backup, name="import"),
    path("templates/", views.templates, name="templates"),
    path("templates/new/", views.template_form, name="template_create"),
    path("templates/<int:pk>/", views.template_form, name="template_edit"),
    path(
        "templates/<int:pk>/delete/",
        views.config_delete,
        {"kind": "template"},
        name="template_delete",
    ),
    path("settings/", views.settings_view, name="settings"),
    path("profiles/new/", views.profile_form, name="profile_create"),
    path("profiles/<int:pk>/", views.profile_form, name="profile_edit"),
    path(
        "profiles/<int:pk>/delete/",
        views.config_delete,
        {"kind": "profile"},
        name="profile_delete",
    ),
    path("attach/<int:content_pk>/", views.attach, name="attach"),
    path("<int:pk>/", views.editor, name="editor"),
    path("<int:pk>/save/", views.save, name="save"),
    path("<int:pk>/preview/", views.preview, name="preview"),
    path("<int:pk>/action/", views.action, name="action"),
    path("<int:pk>/copy/", views.duplicate, name="duplicate"),
    path("<int:pk>/delete/", views.delete, name="delete"),
    path("<int:pk>/download/<str:kind>/", views.download, name="download"),
]
