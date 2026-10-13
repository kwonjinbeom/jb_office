from django.contrib import admin

from .models import Idea, IdeaLog, Stage


class StageInline(admin.TabularInline):
    model = Stage
    extra = 0
    fields = ("order", "title", "status", "due")


@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "category", "status", "priority", "updated_at")
    list_filter = ("category", "status", "priority")
    search_fields = ("code", "title", "customer", "pain", "judgement", "tags")
    ordering = ("code",)
    inlines = [StageInline]


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ("idea", "order", "title", "status", "due", "updated_at")
    list_filter = ("status",)


@admin.register(IdeaLog)
class IdeaLogAdmin(admin.ModelAdmin):
    list_display = ("idea", "stage", "created_at", "body")
    search_fields = ("body",)
