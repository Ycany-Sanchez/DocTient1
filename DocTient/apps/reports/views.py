from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Subquery
from django.shortcuts import redirect, render

from apps.clinic.models import (
    DoctorPatientConnection,
    DoctorNote,
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
        adherence_style = f"width: {adherence_rate}%;"

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
            "adherence_style": adherence_style,
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
    patients = list(PatientProfile.objects.filter(id__in=patient_ids).select_related("user"))

    triage_alerts = []
    normal_patients = []
    all_sys = []
    all_dia = []
    all_hr = []
    all_spo2 = []
    total_meds_prescribed = 0
    total_active_meds = 0

    for p in patients:
        latest = p.vital_signs.first()
        p.latest_vital = latest
        p.active_meds = list(p.medications.filter(status="active"))
        p.total_meds = len(p.active_meds)
        total_meds_prescribed += Medication.objects.filter(doctor=doctor, patient=p).count()
        total_active_meds += Medication.objects.filter(doctor=doctor, patient=p, status="active").count()

        if latest:
            if latest.systolic:
                all_sys.append(latest.systolic)
            if latest.diastolic:
                all_dia.append(latest.diastolic)
            if latest.heart_rate:
                all_hr.append(latest.heart_rate)
            if latest.oxygen_saturation:
                all_spo2.append(float(latest.oxygen_saturation))

        if latest and (
            (latest.systolic and latest.systolic >= 140)
            or (latest.diastolic and latest.diastolic >= 90)
            or (latest.oxygen_saturation and float(latest.oxygen_saturation) < 92)
        ):
            p.triage_level = "High Priority"
            p.triage_badge = "badge-danger"
            triage_alerts.append(p)
        elif latest and (
            (latest.systolic and latest.systolic >= 130)
            or (latest.diastolic and latest.diastolic >= 80)
        ):
            p.triage_level = "Elevated"
            p.triage_badge = "badge-warning"
            normal_patients.append(p)
        else:
            p.triage_level = "Stable"
            p.triage_badge = "badge-success"
            normal_patients.append(p)

        # Recent vitals for per-patient mini table
        p.recent_vitals = list(p.vital_signs.all()[:5])

    # Cohort aggregate statistics
    cohort_avg_sys = round(sum(all_sys) / len(all_sys)) if all_sys else None
    cohort_avg_dia = round(sum(all_dia) / len(all_dia)) if all_dia else None
    cohort_avg_hr = round(sum(all_hr) / len(all_hr)) if all_hr else None
    cohort_avg_spo2 = round(sum(all_spo2) / len(all_spo2), 1) if all_spo2 else None
    controlled_count = len([p for p in patients if p.triage_level == "Stable"])
    controlled_pct = round((controlled_count / len(patients)) * 100) if patients else 0

    # Per-patient drill-down (optional query param)
    detail_patient = None
    detail_vitals = []
    detail_medications = []
    detail_adherence = 100
    detail_connection = None
    detail_id = request.GET.get("patient_id")
    if detail_id:
        try:
            detail_patient = PatientProfile.objects.select_related("user").get(id=detail_id)
            if detail_patient.id in patient_ids:
                detail_vitals = list(detail_patient.vital_signs.all()[:20])
                detail_medications = list(detail_patient.medications.filter(status="active"))
                total_logs = MedicationLog.objects.filter(medication__patient=detail_patient).count()
                taken_logs = MedicationLog.objects.filter(medication__patient=detail_patient, is_taken=True).count()
                detail_adherence = round((taken_logs / total_logs) * 100) if total_logs > 0 else 100
                detail_connection = DoctorPatientConnection.objects.filter(
                    doctor=doctor, patient=detail_patient
                ).first()
        except PatientProfile.DoesNotExist:
            detail_patient = None

    # Doctor notes history
    doctor_notes = list(DoctorNote.objects.filter(doctor=doctor).order_by("-id")[:20])

    return render(request, "reports/reports.html", {
        "is_doctor": True,
        "doctor": doctor,
        "total_cohort": len(patients),
        "triage_alerts": triage_alerts,
        "normal_patients": normal_patients,
        "patients": patients,
        "cohort_avg_sys": cohort_avg_sys,
        "cohort_avg_dia": cohort_avg_dia,
        "cohort_avg_hr": cohort_avg_hr,
        "cohort_avg_spo2": cohort_avg_spo2,
        "controlled_count": controlled_count,
        "controlled_pct": controlled_pct,
        "total_meds_prescribed": total_meds_prescribed,
        "total_active_meds": total_active_meds,
        "detail_patient": detail_patient,
        "detail_vitals": detail_vitals,
        "detail_medications": detail_medications,
        "detail_adherence": detail_adherence,
        "detail_connection": detail_connection,
        "doctor_notes": doctor_notes,
    })


@login_required
def patient_vitals_join_view(request):
    """
    SQL JOIN Implementation (Django ORM select_related):
    Retrieves VitalSign records joined with their related PatientProfile records
    using an SQL INNER JOIN on vital_signs.patient_id = patient_profiles.id.
    """
    vitals = VitalSign.objects.select_related("patient").all()
    generated_sql = str(vitals.query)

    vitals_list = list(vitals)
    unique_patient_count = len({v.patient_id for v in vitals_list})
    alert_count = sum(
        1
        for v in vitals_list
        if (v.systolic and v.systolic >= 140)
        or (v.diastolic and v.diastolic >= 90)
        or (v.oxygen_saturation and float(v.oxygen_saturation) < 92)
    )

    return render(
        request,
        "reports/vitals_join.html",
        {
            "vitals": vitals_list,
            "total_records": len(vitals_list),
            "unique_patient_count": unique_patient_count,
            "alert_count": alert_count,
            "generated_sql": generated_sql,
        },
    )


@login_required
def patients_with_vitals_subquery_view(request):
    """
    SQL SUBQUERY Implementation (Django ORM Subquery):
    Inner query selects patient_id values from vital_signs.
    Outer query filters PatientProfile records whose id appears in the inner query.
    """
    vital_patient_ids = VitalSign.objects.values("patient_id")
    patients = PatientProfile.objects.filter(
        id__in=Subquery(vital_patient_ids)
    ).order_by("id")
    generated_sql = str(patients.query)

    patients_list = list(patients)
    total_patients = PatientProfile.objects.count()
    excluded_patients = max(0, total_patients - len(patients_list))

    return render(
        request,
        "reports/patients_subquery.html",
        {
            "patients": patients_list,
            "matched_count": len(patients_list),
            "total_patients": total_patients,
            "excluded_patients": excluded_patients,
            "generated_sql": generated_sql,
        },
    )


