from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path("play/", views.play_hub, name="play_hub"),
    path("chatbox/", views.chatbox, name="chatbox"),
    path("suggestions/", views.suggestions, name="suggestions"),
    path("subscription/", views.subscription, name="subscription"),
    path("tournaments/", views.tournaments, name="tournaments"),
    path("tournaments/<slug:slug>/", views.tournament_detail, name="tournament_detail"),
    path("game/<slug:slug>/", views.game, name="game"),
    path("api/cricket/", views.cricket_api, name="cricket_api"),
    path("api/cricket/<slug:slug>/", views.cricket_api, name="cricket_api_detail"),
    path("api/play-now/", views.api_play_now, name="api_play_now"),
    path("register/", views.registration, name="registration"),
    path("profile/", views.profile, name="profile"),
    path("logout/", views.logout_view, name="logout"),
]
