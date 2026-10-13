from django.contrib import admin

from .models import Memo


@admin.register(Memo)
class MemoAdmin(admin.ModelAdmin):
    list_display = ("title", "pinned", "tags", "updated_at")
    list_filter = ("pinned",)
    search_fields = ("title", "body", "tags")
