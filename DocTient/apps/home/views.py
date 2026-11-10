from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.clinic.models import (
    DoctorPatientConnection,
    DoctorProfile,
    PatientProfile,
    VitalSign,
    Medication,
    MedicationLog,
    DoctorNote,
)


def _safe_int(val):
    if not val:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_decimal(val):
    if not val:
        return None
    try:
        return Decimal(str(val).strip())
    except (ValueError, TypeError, Exception):
        return None


def _evaluate_vitals(systolic, diastolic, heart_rate, oxygen):
    """Returns clinical alert level and badge class."""
    if systolic and diastolic:
        if systolic >= 140 or diastolic >= 90:
            return "Stage 2 HTN", "badge-danger"
        if systolic >= 130 or diastolic >= 80:
            return "Stage 1 HTN", "badge-warning"
        if systolic >= 120 and diastolic < 80:
            return "Elevated", "badge-warning"
    if oxygen and oxygen < 92:
        return "Low SpO₂", "badge-danger"
    if heart_rate and (heart_rate < 55 or heart_rate > 105):
        return "Abnormal HR", "badge-warning"
    return "Normal", "badge-success"


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

    # ==========================================
    # PATIENT DASHBOARD
    # ==========================================
    if patient is not None:
        if request.method == "POST":
            action = request.POST.get("action")

            # 1. Patient self-logs a vital reading
            if action == "log_vital":
                systolic = _safe_int(request.POST.get("systolic"))
                diastolic = _safe_int(request.POST.get("diastolic"))
                hr = _safe_int(request.POST.get("heart_rate"))
                temp = _safe_decimal(request.POST.get("temperature_celsius"))
                spo2 = _safe_decimal(request.POST.get("oxygen_saturation"))
                weight = _safe_decimal(request.POST.get("weight_kg"))
                notes = (request.POST.get("patient_notes") or "").strip()

                status, _ = _evaluate_vitals(systolic, diastolic, hr, spo2)

                VitalSign.objects.create(
                    patient=patient,
                    systolic=systolic,
                    diastolic=diastolic,
                    heart_rate=hr,
                    temperature_celsius=temp,
                    oxygen_saturation=spo2,
                    weight_kg=weight,
                    monitoring_status=status,
                    patient_notes=notes,
                    recorded_at=timezone.now(),
                )
                messages.success(request, "Vital signs recorded successfully!")
                return redirect("home:home")

            # 2. Patient marks medication taken
            if action == "mark_medication_taken":
                med_id = _safe_int(request.POST.get("medication_id"))
                if med_id:
                    med = Medication.objects.filter(id=med_id, patient=patient).first()
                    if med:
                        MedicationLog.objects.create(
                            medication=med,
                            is_taken=True,
                            taken_at=timezone.now(),
                            scheduled_for=timezone.now(),
                            remarks="Logged via Patient Dashboard",
                        )
                        messages.success(request, f"Marked {med.medication} as taken!")
                return redirect("home:home")

        vitals = list(patient.vital_signs.all()[:50])
        latest = vitals[0] if vitals else None

        # Calculate clinical badges for latest vitals
        eval_status, eval_badge = ("Optimal", "badge-success")
        if latest:
            eval_status, eval_badge = _evaluate_vitals(
                latest.systolic, latest.diastolic, latest.heart_rate, latest.oxygen_saturation
            )

        # Active medications with today's compliance status
        medications = list(patient.medications.filter(status="active").select_related("doctor"))
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for med in medications:
            med.taken_today = med.logs.filter(taken_at__gte=today_start, is_taken=True).exists()

        # Doctor clinical observations
        doctor_conns = list(
            DoctorPatientConnection.objects.filter(patient=patient).select_related("doctor")
        )

        return render(request, "home/home.html", {
            "is_patient": True,
            "patient": patient,
            "vitals": vitals,
            "latest": latest,
            "eval_status": eval_status,
            "eval_badge": eval_badge,
            "medications": medications,
            "doctor_conns": doctor_conns,
        })

    # ==========================================
    # DOCTOR DASHBOARD
    # ==========================================
    connections = list(
        DoctorPatientConnection.objects.filter(doctor=doctor).select_related("patient__user")
    )
    connected_ids = [c.patient_id for c in connections]

    if request.method == "POST":
        action = request.POST.get("action")

        # Doctor adds patient to active roster
        if action == "add_patient":
            username = (request.POST.get("username") or "").strip()
            try:
                target = PatientProfile.objects.select_related("user").get(user__username=username)
                DoctorPatientConnection.objects.get_or_create(doctor=doctor, patient=target)
                messages.success(request, f"Connected with patient {target.full_name} (@{username}).")
            except PatientProfile.DoesNotExist:
                messages.error(request, f"No patient found with username '{username}'.")
            return redirect("home:home")

        # Doctor records vitals for selected patient
        if action == "record_patient_vitals":
            target_id = _safe_int(request.POST.get("patient_id"))
            target_patient = PatientProfile.objects.filter(id=target_id).first()
            if target_patient:
                systolic = _safe_int(request.POST.get("systolic"))
                diastolic = _safe_int(request.POST.get("diastolic"))
                hr = _safe_int(request.POST.get("heart_rate"))
                temp = _safe_decimal(request.POST.get("temperature_celsius"))
                spo2 = _safe_decimal(request.POST.get("oxygen_saturation"))
                weight = _safe_decimal(request.POST.get("weight_kg"))
                status = (request.POST.get("monitoring_status") or "").strip()
                notes = (request.POST.get("patient_notes") or "").strip()

                if not status:
                    status, _ = _evaluate_vitals(systolic, diastolic, hr, spo2)

                VitalSign.objects.create(
                    patient=target_patient,
                    systolic=systolic,
                    diastolic=diastolic,
                    heart_rate=hr,
                    temperature_celsius=temp,
                    oxygen_saturation=spo2,
                    weight_kg=weight,
                    monitoring_status=status,
                    patient_notes=notes,
                    recorded_at=timezone.now(),
                )
                messages.success(request, f"Recorded vital signs for {target_patient.full_name}.")
                return redirect(f"/home/?patient_id={target_patient.id}")

        # Doctor prescribes new medication
        if action == "prescribe_medication":
            target_id = _safe_int(request.POST.get("patient_id"))
            target_patient = PatientProfile.objects.filter(id=target_id).first()
            med_name = (request.POST.get("medication") or "").strip()
            if target_patient and med_name:
                Medication.objects.create(
                    patient=target_patient,
                    doctor=doctor,
                    medication=med_name,
                    dosage=(request.POST.get("dosage") or "").strip(),
                    frequency=(request.POST.get("frequency") or "").strip(),
                    status="active",
                    reminder_active=True,
                )
                messages.success(request, f"Prescribed {med_name} to {target_patient.full_name}.")
                return redirect(f"/home/?patient_id={target_patient.id}")

        # Doctor updates clinical notes and recommendations
        if action == "update_clinical_note":
            target_id = _safe_int(request.POST.get("patient_id"))
            target_patient = PatientProfile.objects.filter(id=target_id).first()
            if target_patient:
                obs = (request.POST.get("observations") or "").strip()
                recom = (request.POST.get("recommendations") or "").strip()
                conn, _ = DoctorPatientConnection.objects.get_or_create(doctor=doctor, patient=target_patient)
                conn.observations = obs
                conn.recommendations = recom
                conn.save()
                messages.success(request, f"Clinical observations updated for {target_patient.full_name}.")
                return redirect(f"/home/?patient_id={target_patient.id}")

    query = (request.GET.get("q") or "").strip()
    selected_id = request.GET.get("patient_id")

    patients = PatientProfile.objects.select_related("user").all().order_by("full_name")
    if query:
        patients = patients.filter(full_name__icontains=query) | patients.filter(user__username__icontains=query)
    patients = list(patients[:50])

    for p in patients:
        p.latest_vital = p.vital_signs.first()
        p.is_connected = p.id in connected_ids
        if p.latest_vital:
            p.eval_status, p.eval_badge = _evaluate_vitals(
                p.latest_vital.systolic,
                p.latest_vital.diastolic,
                p.latest_vital.heart_rate,
                p.latest_vital.oxygen_saturation,
            )
        else:
            p.eval_status, p.eval_badge = ("No Data", "badge-muted")

    selected_patient = None
    selected_vitals = []
    selected_medications = []
    selected_connection = None

    if selected_id:
        try:
            selected_patient = PatientProfile.objects.select_related("user").get(id=selected_id)
            if not connected_ids or selected_patient.id in connected_ids:
                selected_vitals = list(selected_patient.vital_signs.all()[:50])
                selected_medications = list(selected_patient.medications.all())
                selected_connection = DoctorPatientConnection.objects.filter(
                    doctor=doctor, patient=selected_patient
                ).first()
            else:
                messages.warning(request, "Add this patient to your list to access their full chart.")
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
        "selected_medications": selected_medications,
        "selected_connection": selected_connection,
    })
