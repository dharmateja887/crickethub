from django.contrib import admin
from .models import DashboardChatMessage, DashboardSuggestion


@admin.register(DashboardChatMessage)
class DashboardChatMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_user", "is_chatbox", "created_at")
    search_fields = ("user__username", "message")
    list_filter = ("is_user", "is_chatbox", "created_at")


@admin.register(DashboardSuggestion)
class DashboardSuggestionAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "response", "created_at")
    search_fields = ("user__username", "question", "response")
    list_filter = ("created_at",)
