from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from apps.clinic.models import DoctorProfile, PatientProfile


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home:home")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        role = request.POST.get("role", "patient")
        full_name = (request.POST.get("full_name") or "").strip() or username

        if not username or not password:
            return render(request, "register/register.html", {
                "error": "Username and password are required.",
            })
        if role not in ("patient", "doctor"):
            role = "patient"
        if User.objects.filter(username=username).exists():
            return render(request, "register/register.html", {
                "error": "Username already exists.",
            })

        user = User.objects.create_user(username=username, password=password)
        if role == "doctor":
            DoctorProfile.objects.create(
                user=user,
                full_name=full_name,
                med_specialty=(request.POST.get("med_specialty") or "").strip(),
            )
        else:
            PatientProfile.objects.create(user=user, full_name=full_name)
        return redirect("login:login")
    return render(request, "register/register.html")
