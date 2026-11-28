from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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


def _is_ajax(request):
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (request.headers.get("Accept") or "")
    )


def _clamp_pct(val, lo, hi):
    if val is None or hi <= lo:
        return 0
    return round(max(0.0, min(100.0, ((float(val) - lo) / (hi - lo)) * 100.0)), 1)


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


def build_clinical_vital_gauges(latest, vitals_list, patient=None):
    """
    Computes per-vital clinical status, danger-zone bar geometry, and readable thresholds
    for Blood Pressure, Heart Rate, Oxygen Saturation, Temperature, and Body Weight.
    """
    prev = vitals_list[1] if len(vitals_list) > 1 else None

    # 1. Blood Pressure (scale 80..180 mmHg; safe <120, elevated 120-129, warn 130-139, danger >=140)
    bp_sys = latest.systolic if latest and latest.systolic is not None else None
    bp_dia = latest.diastolic if latest and latest.diastolic is not None else None
    if bp_sys is not None and bp_dia is not None:
        if bp_sys >= 140 or bp_dia >= 90:
            bp_state, bp_label = "danger", "Danger"
        elif bp_sys >= 130 or bp_dia >= 80:
            bp_state, bp_label = "warn", "Stage 1"
        elif bp_sys >= 120:
            bp_state, bp_label = "warn", "Elevated"
        elif bp_sys < 90 or bp_dia < 60:
            bp_state, bp_label = "danger", "Low BP"
        else:
            bp_state, bp_label = "normal", "Normal"
        bp_pos = _clamp_pct(bp_sys, 80, 180)
        bp_val = f"{bp_sys}/{bp_dia}"
    else:
        bp_state, bp_label, bp_pos, bp_val = "none", "No data", None, "–"

    # 2. Heart Rate (scale 40..140 bpm; danger <55 or >105, warn 101-105, normal 55-100)
    hr = latest.heart_rate if latest and latest.heart_rate is not None else None
    if hr is not None:
        if hr < 55 or hr > 105:
            hr_state, hr_label = "danger", "Danger"
        elif hr > 100 or hr < 60:
            hr_state, hr_label = "warn", "Borderline"
        else:
            hr_state, hr_label = "normal", "Normal"
        hr_pos = _clamp_pct(hr, 40, 140)
        hr_val = f"{hr}"
    else:
        hr_state, hr_label, hr_pos, hr_val = "none", "No data", None, "–"

    # 3. Oxygen Saturation SpO2 (scale 85..100%; danger <92, warn 92-94.9, normal >=95)
    spo2 = float(latest.oxygen_saturation) if latest and latest.oxygen_saturation is not None else None
    if spo2 is not None:
        if spo2 < 92.0:
            spo2_state, spo2_label = "danger", "Danger"
        elif spo2 < 95.0:
            spo2_state, spo2_label = "warn", "Low"
        else:
            spo2_state, spo2_label = "normal", "Normal"
        spo2_pos = _clamp_pct(spo2, 85, 100)
        spo2_val = f"{spo2:.1f}" if spo2 % 1 else f"{int(spo2)}"
    else:
        spo2_state, spo2_label, spo2_pos, spo2_val = "none", "No data", None, "–"

    # 4. Temperature (scale 34.5..40.0 C; danger <35.5 or >=38.0, warn 37.5-37.9, normal 35.5-37.4)
    temp = float(latest.temperature_celsius) if latest and latest.temperature_celsius is not None else None
    if temp is not None:
        if temp >= 38.0 or temp < 35.5:
            temp_state, temp_label = "danger", "Fever" if temp >= 38.0 else "Low temp"
        elif temp >= 37.5:
            temp_state, temp_label = "warn", "Elevated"
        else:
            temp_state, temp_label = "normal", "Normal"
        temp_pos = _clamp_pct(temp, 34.5, 40.0)
        temp_val = f"{temp:.1f}"
    else:
        temp_state, temp_label, temp_pos, temp_val = "none", "No data", None, "–"

    # 5. Body Weight & optional BMI (scale 40..120 kg or BMI 15..35)
    wt = float(latest.weight_kg) if latest and latest.weight_kg is not None else (
        float(patient.weight_kg) if patient and patient.weight_kg is not None else None
    )
    prev_wt = float(prev.weight_kg) if prev and prev.weight_kg is not None else None
    height_cm = float(patient.height_cm) if patient and patient.height_cm else None
    if wt is not None:
        wt_val = f"{wt:.1f}"
        if height_cm and height_cm > 0:
            bmi = round(wt / ((height_cm / 100.0) ** 2), 1)
            if bmi >= 30.0 or bmi < 16.5:
                wt_state, wt_label = "danger", f"BMI {bmi}"
            elif bmi >= 25.0 or bmi < 18.5:
                wt_state, wt_label = "warn", f"BMI {bmi}"
            else:
                wt_state, wt_label = "normal", f"BMI {bmi}"
            wt_pos = _clamp_pct(bmi, 15.0, 35.0)
            wt_range_note = "Normal BMI 18.5–24.9 · Risk ≥30"
            wt_zones = {"warn_start": 50.0, "danger_start": 75.0, "danger_low_end": 17.5}
        else:
            diff = round(wt - prev_wt, 1) if prev_wt is not None else 0.0
            if abs(diff) >= 3.0:
                wt_state, wt_label = "warn", f"{'+' if diff > 0 else '−'}{abs(diff):.1f} kg"
            else:
                wt_state, wt_label = "normal", "Stable"
            wt_pos = _clamp_pct(wt, 40.0, 120.0)
            wt_range_note = (
                f"{'+' if diff > 0 else '−'}{abs(diff):.1f} kg vs prior"
                if prev_wt is not None and diff != 0
                else "No change vs prior"
            )
            wt_zones = {"warn_start": 75.0, "danger_start": 88.0, "danger_low_end": 6.0}
    else:
        wt_state, wt_label, wt_pos, wt_val = "none", "No data", None, "–"
        wt_range_note = "Log weight to track trend"
        wt_zones = {"warn_start": 75.0, "danger_start": 88.0, "danger_low_end": 6.0}

    return [
        {
            "key": "bp",
            "name": "Blood pressure",
            "value": bp_val,
            "unit": "mmHg",
            "state": bp_state,
            "state_label": bp_label,
            "marker_pct": bp_pos,
            "range_note": "Limit ≥140/90",
            # Zones on 80..180 scale: low danger 0..10%, safe 10..40%, warn 40..60%, high danger 60..100%
            "danger_low_end": 10.0,
            "warn_start": 40.0,
            "danger_start": 60.0,
        },
        {
            "key": "hr",
            "name": "Heart rate",
            "value": hr_val,
            "unit": "bpm",
            "state": hr_state,
            "state_label": hr_label,
            "marker_pct": hr_pos,
            "range_note": "55–105 bpm",
            # Scale 40..140: low danger 0..15%, safe 15..60%, warn 60..65%, high danger 65..100%
            "danger_low_end": 15.0,
            "warn_start": 60.0,
            "danger_start": 65.0,
        },
        {
            "key": "spo2",
            "name": "Oxygen SpO₂",
            "value": spo2_val,
            "unit": "%",
            "state": spo2_state,
            "state_label": spo2_label,
            "marker_pct": spo2_pos,
            "range_note": "Min 92%",
            # Scale 85..100: low danger 0..46.7% (<92), warn 46.7..66.7% (92-95), safe 66.7..100%
            "danger_low_end": 46.7,
            "warn_low_end": 66.7,
            "warn_start": 100.0,
            "danger_start": 100.0,
        },
        {
            "key": "temp",
            "name": "Temperature",
            "value": temp_val,
            "unit": "°C",
            "state": temp_state,
            "state_label": temp_label,
            "marker_pct": temp_pos,
            "range_note": "Max 38.0°C",
            # Scale 34.5..40.0 (span 5.5): low danger <35.5 (18.2%), warn 37.5..38.0 (54.5..63.6%), danger >=38.0 (63.6%+)
            "danger_low_end": 18.2,
            "warn_start": 54.5,
            "danger_start": 63.6,
        },
        {
            "key": "weight",
            "name": "Body weight",
            "value": wt_val,
            "unit": "kg",
            "state": wt_state,
            "state_label": wt_label,
            "marker_pct": wt_pos,
            "range_note": wt_range_note,
            "danger_low_end": wt_zones["danger_low_end"],
            "warn_start": wt_zones["warn_start"],
            "danger_start": wt_zones["danger_start"],
        },
    ]


def build_vitals_chart_payload(vitals_list):
    """Builds chronological JSON-safe arrays for all 5 vitals (oldest → newest, max 14 readings)."""
    chron = list(reversed(vitals_list[:14]))
    labels = [timezone.localtime(v.recorded_at).strftime("%b %d") for v in chron]
    full_dates = [timezone.localtime(v.recorded_at).strftime("%b %d, %Y %H:%M") for v in chron]
    return {
        "labels": labels,
        "fullDates": full_dates,
        "systolic": [v.systolic for v in chron],
        "diastolic": [v.diastolic for v in chron],
        "heartRate": [v.heart_rate for v in chron],
        "spo2": [float(v.oxygen_saturation) if v.oxygen_saturation is not None else None for v in chron],
        "temperature": [float(v.temperature_celsius) if v.temperature_celsius is not None else None for v in chron],
        "weight": [float(v.weight_kg) if v.weight_kg is not None else None for v in chron],
        "status": [v.monitoring_status or "Normal" for v in chron],
    }


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
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

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
                messages.success(request, "Vital signs recorded successfully.")
                return redirect("home:home")

            # 2. Patient marks or toggles medication taken (supports zero-refresh AJAX + plain POST fallback)
            if action in ("mark_medication_taken", "toggle_medication_taken"):
                med_id = _safe_int(request.POST.get("medication_id"))
                med = Medication.objects.filter(id=med_id, patient=patient).first() if med_id else None
                taken_now = False
                if med:
                    existing_today = med.logs.filter(taken_at__gte=today_start, is_taken=True)
                    if action == "toggle_medication_taken" and existing_today.exists():
                        existing_today.delete()
                        taken_now = False
                    else:
                        if not existing_today.exists():
                            MedicationLog.objects.create(
                                medication=med,
                                is_taken=True,
                                taken_at=timezone.now(),
                                scheduled_for=timezone.now(),
                                remarks="Logged via Patient Dashboard",
                            )
                        taken_now = True

                if _is_ajax(request):
                    if not med:
                        return JsonResponse({"ok": False, "error": "Medication not found."}, status=404)
                    active_meds = list(patient.medications.filter(status="active"))
                    total_active = len(active_meds)
                    taken_count = sum(
                        1 for m in active_meds
                        if m.logs.filter(taken_at__gte=today_start, is_taken=True).exists()
                    )
                    adherence_pct = round((taken_count / total_active) * 100) if total_active else 0
                    return JsonResponse({
                        "ok": True,
                        "medication_id": med.id,
                        "medication_name": med.medication,
                        "taken_today": taken_now,
                        "taken_today_count": taken_count,
                        "total_active_meds": total_active,
                        "today_adherence_pct": adherence_pct,
                        "due_count": max(0, total_active - taken_count),
                    })

                if med:
                    messages.success(request, f"Marked {med.medication} as taken.")
                return redirect("home:home")

        vitals = list(patient.vital_signs.all()[:50])
        latest = vitals[0] if vitals else None

        # Calculate clinical badges for latest vitals
        eval_status, eval_badge = ("Normal", "badge-success")
        if latest:
            eval_status, eval_badge = _evaluate_vitals(
                latest.systolic, latest.diastolic, latest.heart_rate, latest.oxygen_saturation
            )

        # Active medications with today's compliance status
        medications = list(patient.medications.filter(status="active").select_related("doctor"))
        for med in medications:
            med.taken_today = med.logs.filter(taken_at__gte=today_start, is_taken=True).exists()

        taken_today_count = sum(1 for m in medications if m.taken_today)
        total_active_meds = len(medications)
        due_today_count = max(0, total_active_meds - taken_today_count)
        today_adherence_pct = (
            round((taken_today_count / total_active_meds) * 100) if total_active_meds > 0 else 0
        )

        # Clinical gauges (for all 5 vitals with danger bars) + chart dataset
        vital_gauges = build_clinical_vital_gauges(latest, vitals, patient=patient)
        vitals_chart_data = build_vitals_chart_payload(vitals)
        danger_gauges = [g for g in vital_gauges if g["state"] == "danger"]
        warn_gauges = [g for g in vital_gauges if g["state"] == "warn"]

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
            "vital_gauges": vital_gauges,
            "vitals_chart_data": vitals_chart_data,
            "danger_gauges": danger_gauges,
            "warn_gauges": warn_gauges,
            "medications": medications,
            "taken_today_count": taken_today_count,
            "total_active_meds": total_active_meds,
            "due_today_count": due_today_count,
            "today_adherence_pct": today_adherence_pct,
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
                if obs or recom:
                    DoctorNote.objects.create(
                        doctor=doctor,
                        patient=target_patient,
                        observations=obs,
                        recommendations=recom,
                    )
                messages.success(request, f"Clinical observations updated for {target_patient.full_name}.")
                return redirect(f"/home/?patient_id={target_patient.id}")

        # Doctor toggles medication status (Active vs Discontinued) — supports zero-refresh AJAX
        if action == "toggle_med_status":
            target_id = _safe_int(request.POST.get("patient_id"))
            med_id = _safe_int(request.POST.get("medication_id"))
            med = Medication.objects.filter(id=med_id).first() if med_id else None
            updated = False
            if med and (med.doctor == doctor or med.patient.id in connected_ids):
                med.status = "discontinued" if med.status == "active" else "active"
                med.save()
                updated = True

            if _is_ajax(request):
                if not updated:
                    return JsonResponse({"ok": False, "error": "Unable to update prescription."}, status=403)
                return JsonResponse({
                    "ok": True,
                    "medication_id": med.id,
                    "status": med.status,
                    "status_label": med.status.title(),
                })

            if updated:
                messages.success(request, f"Updated {med.medication} status to {med.status.title()}.")
            return redirect(f"/home/?patient_id={target_id}" if target_id else "home:home")

    query = (request.GET.get("q") or "").strip()
    selected_id = request.GET.get("patient_id")

    if query:
        like_q = f"%{query}%"
        patients = list(
            PatientProfile.objects.raw(
                """
                SELECT p.id, p.user_id, p.full_name, a.username, p.date_of_birth, p.gender, a.email
                FROM patient_profiles p
                INNER JOIN auth_user a ON (p.user_id = a.id)
                WHERE LOWER(p.full_name) LIKE LOWER(%s)
                   OR LOWER(a.username) LIKE LOWER(%s)
                ORDER BY p.full_name ASC
                LIMIT 50
                """,
                [like_q, like_q],
            )
        )
    else:
        patients = list(
            PatientProfile.objects.raw(
                """
                SELECT p.id, p.user_id, p.full_name, a.username, p.date_of_birth, p.gender, a.email
                FROM patient_profiles p
                INNER JOIN auth_user a ON (p.user_id = a.id)
                ORDER BY p.full_name ASC
                LIMIT 50
                """
            )
        )

    triage_alert_count = 0
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
            p.bp_marker_pct = _clamp_pct(p.latest_vital.systolic, 80, 180) if p.latest_vital.systolic else None
            if p.eval_badge == "badge-danger":
                triage_alert_count += 1
        else:
            p.eval_status, p.eval_badge = ("No data", "badge-muted")
            p.bp_marker_pct = None

    selected_patient = None
    selected_vitals = []
    selected_medications = []
    selected_connection = None
    selected_gauges = []
    selected_chart_data = None
    recent_notes = []

    if selected_id:
        try:
            selected_patient = PatientProfile.objects.select_related("user").get(id=selected_id)
            if not connected_ids or selected_patient.id in connected_ids:
                selected_vitals = list(selected_patient.vital_signs.all()[:50])
                selected_medications = list(selected_patient.medications.all().select_related("doctor"))
                for med in selected_medications:
                    med.taken_count = med.logs.filter(is_taken=True).count()
                    med.total_logs = med.logs.count()
                selected_connection = DoctorPatientConnection.objects.filter(
                    doctor=doctor, patient=selected_patient
                ).first()
                selected_gauges = build_clinical_vital_gauges(
                    selected_vitals[0] if selected_vitals else None,
                    selected_vitals,
                    patient=selected_patient,
                )
                selected_chart_data = build_vitals_chart_payload(selected_vitals)
                recent_notes = list(
                    DoctorNote.objects.filter(doctor=doctor, patient=selected_patient).order_by("-created_at", "-id")[:5]
                )
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
        "triage_alert_count": triage_alert_count,
        "query": query,
        "selected_patient": selected_patient,
        "selected_vitals": selected_vitals,
        "selected_medications": selected_medications,
        "selected_connection": selected_connection,
        "selected_gauges": selected_gauges,
        "selected_chart_data": selected_chart_data,
        "recent_notes": recent_notes,
    })
