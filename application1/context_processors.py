from .models import Profile, Subscription


def current_profile(request):
    ctx = {}
    if request.user.is_authenticated:
        ctx["current_profile"] = Profile.objects.filter(user=request.user).order_by("-id").first()
        ctx["current_subscription"] = Subscription.objects.filter(user=request.user).order_by("-id").first()
    return ctx
