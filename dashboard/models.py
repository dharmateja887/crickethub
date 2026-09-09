from django.contrib.auth.models import User
from django.db import models


class DashboardChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    is_user = models.BooleanField(default=True)
    is_chatbox = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Chat Messages"

    def __str__(self):
        return f"{'User' if self.is_user else 'Bot'}: {self.message[:50]}"


class DashboardSuggestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    question = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Suggestions"

    def __str__(self):
        return f"Q: {self.question[:50]}"
