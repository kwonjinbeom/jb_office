from django.contrib import admin

from .models import Idea


@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "category", "status", "priority", "updated_at")
    list_filter = ("category", "status", "priority")
    search_fields = ("code", "title", "customer", "pain", "judgement", "tags")
    ordering = ("code",)
