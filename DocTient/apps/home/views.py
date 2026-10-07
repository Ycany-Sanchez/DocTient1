from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.clinic.models import (
    DoctorPatientConnection,
    DoctorProfile,
    PatientProfile,
)


@login_required
def home_view(request):
    doctor = DoctorProfile.objects.filter(user=request.user).first()
    patient = PatientProfile.objects.filter(user=request.user).first()

    # Existing users with no role yet: let them pick once.
    if doctor is None and patient is None:
        if request.method == "POST":
            role = request.POST.get("role", "patient")
            full_name = (request.POST.get("full_name") or "").strip() or request.user.username
            if role == "doctor":
                DoctorProfile.objects.create(
                    user=request.user,
                    full_name=full_name,
                    med_specialty=(request.POST.get("med_specialty") or "").strip(),
                )
                messages.success(request, "Doctor profile created.")
            else:
                PatientProfile.objects.create(user=request.user, full_name=full_name)
                messages.success(request, "Patient profile created.")
            return redirect("home:home")
        return render(request, "home/home.html", {"needs_role": True})

    # --- Patient dashboard: read-only own vitals ---
    if patient is not None:
        vitals = list(patient.vital_signs.all()[:50])
        latest = vitals[0] if vitals else None
        return render(request, "home/home.html", {
            "is_patient": True,
            "patient": patient,
            "vitals": vitals,
            "latest": latest,
        })

    # --- Doctor dashboard: read-only patients' vitals ---
    connections = list(
        DoctorPatientConnection.objects.filter(doctor=doctor).select_related("patient__user")
    )
    connected_ids = [c.patient_id for c in connections]

    if request.method == "POST" and request.POST.get("action") == "add_patient":
        username = (request.POST.get("username") or "").strip()
        try:
            target = PatientProfile.objects.select_related("user").get(user__username=username)
            DoctorPatientConnection.objects.get_or_create(doctor=doctor, patient=target)
            messages.success(request, f"Added patient {username}.")
        except PatientProfile.DoesNotExist:
            messages.error(request, f"No patient found with username '{username}'.")
        return redirect("home:home")

    query = (request.GET.get("q") or "").strip()
    selected_id = request.GET.get("patient_id")

    patients = PatientProfile.objects.select_related("user").all().order_by("full_name")
    if query:
        patients = patients.filter(full_name__icontains=query) | patients.filter(user__username__icontains=query)
    patients = list(patients[:50])

    # Vitals preview per listed patient (latest only to keep it light).
    for p in patients:
        p.latest_vital = p.vital_signs.first()
        p.is_connected = p.id in connected_ids

    selected_patient = None
    selected_vitals = []
    if selected_id:
        try:
            selected_patient = PatientProfile.objects.select_related("user").get(id=selected_id)
            # Only allow viewing connected patients, or any if doctor has no connections yet.
            if not connected_ids or selected_patient.id in connected_ids:
                selected_vitals = list(selected_patient.vital_signs.all()[:50])
            else:
                messages.error(request, "Add this patient to your list first.")
                selected_patient = None
        except PatientProfile.DoesNotExist:
            selected_patient = None

    my_patients = [p for p in patients if p.id in connected_ids] if connected_ids else []

    return render(request, "home/home.html", {
        "is_doctor": True,
        "doctor": doctor,
        "patients": patients,
        "my_patients": my_patients,
        "connected_ids": connected_ids,
        "query": query,
        "selected_patient": selected_patient,
        "selected_vitals": selected_vitals,
    })
