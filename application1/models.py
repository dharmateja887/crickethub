from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=120, blank=True, default="Guest Player")
    email = models.EmailField(blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=120, blank=True)
    about = models.TextField(blank=True)
    avatar_data = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or self.mobile or "Unknown"


class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    plan_name = models.CharField(max_length=100)
    price = models.IntegerField()
    payment_method = models.CharField(max_length=30, blank=True, default="card")
    transaction_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default="active")
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.plan_name} - {self.user}"


class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    is_user = models.BooleanField(default=True)
    is_chatbox = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{'User' if self.is_user else 'Bot'}: {self.message[:50]}"
