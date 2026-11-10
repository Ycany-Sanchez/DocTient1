from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.clinic.models import DoctorProfile, PatientProfile
from .models import Profile


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    doctor = DoctorProfile.objects.filter(user=request.user).first()
    patient = PatientProfile.objects.filter(user=request.user).first()

    if request.method == "POST":
        profile.full_name = (request.POST.get("full_name") or "").strip()
        profile.bio = (request.POST.get("bio") or "").strip()
        if "profile_image" in request.FILES:
            profile.profile_image = request.FILES["profile_image"]
        profile.save()

        # Update clinical profiles
        if patient:
            patient.full_name = profile.full_name or patient.full_name
            patient.contact_no = (request.POST.get("contact_no") or "").strip()
            patient.emergency_contact_no = (request.POST.get("emergency_contact_no") or "").strip()
            patient.address = (request.POST.get("address") or "").strip()
            patient.gender = (request.POST.get("gender") or "").strip()
            patient.save()

        if doctor:
            doctor.full_name = profile.full_name or doctor.full_name
            doctor.med_specialty = (request.POST.get("med_specialty") or "").strip()
            doctor.contact_no = (request.POST.get("contact_no") or "").strip()
            doctor.availability_status = (request.POST.get("availability_status") or "available").strip()
            doctor.bio = profile.bio
            doctor.save()

        messages.success(request, "Profile updated successfully.")
        return redirect("profile:profile")

    return render(request, "profile/profile.html", {
        "profile": profile,
        "doctor": doctor,
        "patient": patient,
    })
