from django.contrib import admin

admin.site.site_header = "JB Office 관리화면"
admin.site.site_title = "관리화면"
admin.site.index_title = "데이터 관리"
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("apps.core.urls")),
    path("daily-ideas/", include("apps.daily_ideas.urls")),
    path("ideas/", include("apps.ideas.urls")),
    path("evidence/", include("apps.evidence.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("memos/", include("apps.memos.urls")),
    path("docs/", include("apps.docs.urls")),
    path("blog/writing/", include("apps.writing.urls")),
    path("blog/naver-writing/", include("apps.naver_writing.urls")),
    path("blog/types/", include("apps.blog_types.urls")),
    path("blog/posts/", include("apps.blog_types.posts_urls")),
    path("blog/site-templates/", include("apps.site_templates.urls")),
    path("blog/rules/", include("apps.blog_rules.urls")),
    path("blog/ops/", include("apps.blog_ops.urls")),
    path("routines/", include("apps.routines.urls")),
    path("series/", include("apps.series.urls")),
    path("anime/", include("apps.anime.urls")),
    path("anime-seasons/", include("apps.anime_seasons.urls")),
    path("schedule/", include("apps.schedule.urls")),
    path("studio/", include("apps.studio.urls")),
    path("blog/", include(("apps.content.urls", "blog"), namespace="blog")),
    path("video/", include(("apps.content.urls", "video"), namespace="video")),
    path("discussions/", include("apps.discussions.urls")),
]
