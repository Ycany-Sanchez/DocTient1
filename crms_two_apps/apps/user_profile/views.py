from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Profile

@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.full_name = request.POST.get("full_name", "")
        profile.bio = request.POST.get("bio", "")
        if "profile_image" in request.FILES:
            profile.profile_image = request.FILES["profile_image"]
        profile.save()
        return redirect("profile:profile")
    return render(request, "profile/profile.html", {"profile": profile})
