from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.clinic.models import (
    DoctorPatientConnection,
    DoctorProfile,
    PatientProfile,
    VitalSign,
    Medication,
    MedicationLog,
)


def _calculate_bmi(weight_kg, height_cm):
    if not weight_kg or not height_cm or height_cm <= 0:
        return None, None
    try:
        height_m = float(height_cm) / 100.0
        bmi = float(weight_kg) / (height_m * height_m)
        bmi_val = round(bmi, 1)
        if bmi_val < 18.5:
            cat = "Underweight"
        elif bmi_val < 25.0:
            cat = "Normal Weight"
        elif bmi_val < 30.0:
            cat = "Overweight"
        else:
            cat = "Obese"
        return bmi_val, cat
    except (ZeroDivisionError, ValueError, TypeError):
        return None, None


@login_required
def reports_view(request):
    doctor = DoctorProfile.objects.filter(user=request.user).first()
    patient = PatientProfile.objects.filter(user=request.user).first()

    if doctor is None and patient is None:
        messages.info(request, "Please set up your profile role first.")
        return redirect("home:home")

    # ==========================================
    # PATIENT REPORT VIEW
    # ==========================================
    if patient is not None:
        vitals = list(patient.vital_signs.all())
        total_readings = len(vitals)

        avg_sys, avg_dia, avg_hr, avg_spo2, avg_temp = None, None, None, None, None
        min_sys, max_sys = None, None
        pulse_pressure = None
        bp_classification = "No Data"
        bp_badge = "badge-muted"

        if total_readings > 0:
            sys_vals = [v.systolic for v in vitals if v.systolic is not None]
            dia_vals = [v.diastolic for v in vitals if v.diastolic is not None]
            hr_vals = [v.heart_rate for v in vitals if v.heart_rate is not None]
            spo2_vals = [float(v.oxygen_saturation) for v in vitals if v.oxygen_saturation is not None]
            temp_vals = [float(v.temperature_celsius) for v in vitals if v.temperature_celsius is not None]

            if sys_vals:
                avg_sys = round(sum(sys_vals) / len(sys_vals))
                min_sys = min(sys_vals)
                max_sys = max(sys_vals)
            if dia_vals:
                avg_dia = round(sum(dia_vals) / len(dia_vals))
            if avg_sys and avg_dia:
                pulse_pressure = avg_sys - avg_dia
                if avg_sys < 120 and avg_dia < 80:
                    bp_classification = "Optimal / Normal"
                    bp_badge = "badge-success"
                elif avg_sys <= 129 and avg_dia < 80:
                    bp_classification = "Elevated"
                    bp_badge = "badge-warning"
                elif avg_sys >= 140 or avg_dia >= 90:
                    bp_classification = "Stage 2 Hypertension"
                    bp_badge = "badge-danger"
                else:
                    bp_classification = "Stage 1 Hypertension"
                    bp_badge = "badge-warning"

            if hr_vals:
                avg_hr = round(sum(hr_vals) / len(hr_vals))
            if spo2_vals:
                avg_spo2 = round(sum(spo2_vals) / len(spo2_vals), 1)
            if temp_vals:
                avg_temp = round(sum(temp_vals) / len(temp_vals), 1)

        # BMI
        latest_vital = vitals[0] if vitals else None
        current_weight = latest_vital.weight_kg if latest_vital and latest_vital.weight_kg else patient.weight_kg
        bmi_value, bmi_category = _calculate_bmi(current_weight, patient.height_cm)

        # Medication Compliance Rate
        medications = list(patient.medications.all())
        total_med_logs = MedicationLog.objects.filter(medication__patient=patient).count()
        taken_med_logs = MedicationLog.objects.filter(medication__patient=patient, is_taken=True).count()
        adherence_rate = (
            round((taken_med_logs / total_med_logs) * 100) if total_med_logs > 0 else 100
        )

        # Chronological readings for trend chart (oldest to newest, max 10)
        trend_readings = list(reversed(vitals[:10]))
        chart_points = []
        trend_polyline_points = ""
        trend_area_path = ""
        n_points = len(trend_readings)

        if n_points > 0:
            pad_left = 30
            pad_right = 30
            canvas_width = 600
            usable_width = canvas_width - pad_left - pad_right

            for i, v in enumerate(trend_readings):
                if n_points == 1:
                    x = canvas_width / 2
                else:
                    x = pad_left + (i / (n_points - 1)) * usable_width

                sys_val = v.systolic if v.systolic is not None else 120
                # 120 mmHg maps to y=60; 1.8 px per mmHg
                y = max(18.0, min(108.0, round(60.0 - (sys_val - 120) * 1.8, 1)))

                chart_points.append({
                    "x": round(x, 1),
                    "y": y,
                    "y_label": max(14.0, y - 8),
                    "systolic": sys_val,
                    "diastolic": v.diastolic,
                    "vital": v,
                })

            trend_polyline_points = " ".join(f"{pt['x']},{pt['y']}" for pt in chart_points)
            if n_points > 1:
                trend_area_path = (
                    f"M {chart_points[0]['x']},{chart_points[0]['y']} "
                    + " ".join(f"L {pt['x']},{pt['y']}" for pt in chart_points)
                    + f" L {chart_points[-1]['x']},120 L {chart_points[0]['x']},120 Z"
                )

        return render(request, "reports/reports.html", {
            "is_patient": True,
            "patient": patient,
            "total_readings": total_readings,
            "avg_sys": avg_sys,
            "avg_dia": avg_dia,
            "min_sys": min_sys,
            "max_sys": max_sys,
            "pulse_pressure": pulse_pressure,
            "bp_classification": bp_classification,
            "bp_badge": bp_badge,
            "avg_hr": avg_hr,
            "avg_spo2": avg_spo2,
            "avg_temp": avg_temp,
            "current_weight": current_weight,
            "bmi_value": bmi_value,
            "bmi_category": bmi_category,
            "medications": medications,
            "adherence_rate": adherence_rate,
            "trend_readings": trend_readings,
            "chart_points": chart_points,
            "trend_polyline_points": trend_polyline_points,
            "trend_area_path": trend_area_path,
            "latest_vital": latest_vital,
        })

    # ==========================================
    # DOCTOR COHORT REPORT VIEW
    # ==========================================
    connections = list(
        DoctorPatientConnection.objects.filter(doctor=doctor).select_related("patient__user")
    )
    patient_ids = [c.patient_id for c in connections]
    patients = PatientProfile.objects.filter(id__in=patient_ids).select_related("user")

    triage_alerts = []
    normal_patients = []
    for p in patients:
        latest = p.vital_signs.first()
        p.latest_vital = latest
        if latest and (
            (latest.systolic and latest.systolic >= 140)
            or (latest.diastolic and latest.diastolic >= 90)
            or (latest.oxygen_saturation and float(latest.oxygen_saturation) < 92)
        ):
            triage_alerts.append(p)
        else:
            normal_patients.append(p)

    return render(request, "reports/reports.html", {
        "is_doctor": True,
        "doctor": doctor,
        "total_cohort": len(patients),
        "triage_alerts": triage_alerts,
        "normal_patients": normal_patients,
        "patients": patients,
    })

