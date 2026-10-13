from django.contrib import admin

from .models import Evidence


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("display_title", "kind", "idea", "stage", "captured_at")
    list_filter = ("kind",)
    search_fields = ("title", "url", "note")
