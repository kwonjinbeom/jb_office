from django.urls import path

from . import views

app_name = "ideas"

urlpatterns = [
    path("", views.idea_list, name="list"),
    path("new/", views.idea_create, name="create"),
    path("<int:pk>/", views.idea_detail, name="detail"),
    path("<int:pk>/edit/", views.idea_edit, name="edit"),
    path("<int:pk>/delete/", views.idea_delete, name="delete"),
    # 단계
    path("<int:pk>/stages/quick/", views.stage_quick_add, name="stage_quick_add"),
    path("<int:pk>/stages/<int:stage_pk>/edit/", views.stage_edit, name="stage_edit"),
    path("<int:pk>/stages/<int:stage_pk>/status/", views.stage_set_status, name="stage_status"),
    path("<int:pk>/stages/<int:stage_pk>/move/", views.stage_move, name="stage_move"),
    path("<int:pk>/stages/<int:stage_pk>/delete/", views.stage_delete, name="stage_delete"),
    # 작업 로그
    path("<int:pk>/logs/add/", views.log_add, name="log_add"),
    path("<int:pk>/logs/<int:log_pk>/delete/", views.log_delete, name="log_delete"),
]
