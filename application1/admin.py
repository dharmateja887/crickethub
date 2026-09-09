from django.contrib import admin
from .models import ChatMessage, Profile, Subscription


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "mobile", "location", "updated_at")
    search_fields = ("full_name", "email", "mobile", "location")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("plan_name", "user", "price", "payment_method", "status", "start_date")
    search_fields = ("plan_name", "user__username", "transaction_id")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_user", "created_at")
    search_fields = ("user__username", "message")
