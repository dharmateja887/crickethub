from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import DashboardChatMessage, DashboardSuggestion


@login_required
def dashboard_home(request):
    chat_messages = DashboardChatMessage.objects.filter(is_chatbox=True).order_by('-created_at')
    suggestions = DashboardSuggestion.objects.all().order_by('-created_at')

    context = {
        'chat_messages': chat_messages,
        'suggestions': suggestions,
        'total_chatbox': chat_messages.count(),
        'total_suggestions': suggestions.count(),
    }
    return render(request, 'dashboard/index.html', context)
