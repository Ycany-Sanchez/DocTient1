from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect

def login_view(request):
    if request.user.is_authenticated:
        return redirect("home:home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home:home")
        return render(request, "login/login.html", {
            "error": "Invalid username or password."
        })
    return render(request, "login/login.html")
