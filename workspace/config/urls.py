from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("apps.core.urls")),
    path("ideas/", include("apps.ideas.urls")),
    path("evidence/", include("apps.evidence.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("memos/", include("apps.memos.urls")),
    path("docs/", include("apps.docs.urls")),
]
