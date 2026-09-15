from django.contrib.auth.models import User
from django.shortcuts import render, redirect

def register_view(request):
    if request.user.is_authenticated:
        return redirect("home:home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        if User.objects.filter(username=username).exists():
            return render(request, "register/register.html", {
                "error": "Username already exists."
            })
        User.objects.create_user(
            username=username,
            password=password
        )
        return redirect("login:login")
    return render(request, "register/register.html")
