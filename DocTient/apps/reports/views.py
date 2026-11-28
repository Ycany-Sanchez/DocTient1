import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.clinic.models import (
    DoctorPatientConnection,
    DoctorNote,
    DoctorProfile,
    PatientProfile,
    VitalSign,
    Medication,
    MedicationLog,
)
from apps.home.views import build_clinical_vital_gauges, build_vitals_chart_payload, _clamp_pct


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


def _filter_vitals_by_range(queryset, range_key):
    now = timezone.now()
    if range_key == "7d":
        return queryset.filter(recorded_at__gte=now - timedelta(days=7)), "Last 7 days"
    if range_key == "30d":
        return queryset.filter(recorded_at__gte=now - timedelta(days=30)), "Last 30 days"
    return queryset, "All sessions"


def _classify_reading_zone(v):
    sys_v = v.systolic
    dia_v = v.diastolic
    spo2_v = float(v.oxygen_saturation) if v.oxygen_saturation is not None else None
    temp_v = float(v.temperature_celsius) if v.temperature_celsius is not None else None
    hr_v = v.heart_rate

    if (
        (sys_v is not None and sys_v >= 140)
        or (dia_v is not None and dia_v >= 90)
        or (spo2_v is not None and spo2_v < 92.0)
        or (temp_v is not None and (temp_v >= 38.0 or temp_v < 35.5))
        or (hr_v is not None and (hr_v < 55 or hr_v > 105))
    ):
        return "danger"
    if (
        (sys_v is not None and sys_v >= 130)
        or (dia_v is not None and dia_v >= 80)
        or (spo2_v is not None and spo2_v < 95.0)
    ):
        return "stage1"
    if (
        (sys_v is not None and sys_v >= 120)
        or (temp_v is not None and temp_v >= 37.5)
    ):
        return "elevated"
    return "normal"


def _build_risk_distribution(vitals):
    total = len(vitals)
    counts = {"normal": 0, "elevated": 0, "stage1": 0, "danger": 0}
    for v in vitals:
        counts[_classify_reading_zone(v)] += 1

    defs = [
        ("normal", "Normal", "BP <120/80 · SpO₂ ≥95% · HR 55–105", "pos"),
        ("elevated", "Elevated", "Systolic 120–129 or temp 37.5–37.9°C", "warn"),
        ("stage1", "Stage 1 HTN", "BP 130–139 / 80–89 or SpO₂ 92–94%", "warn"),
        ("danger", "Danger / Alert", "BP ≥140/90, SpO₂ <92%, or fever ≥38°C", "neg"),
    ]
    rows = []
    for key, label, criteria, tone in defs:
        c = counts[key]
        pct = round((c / total) * 100) if total > 0 else 0
        rows.append({
            "key": key,
            "label": label,
            "criteria": criteria,
            "tone": tone,
            "count": c,
            "pct": pct,
        })
    return rows


def _build_vital_spreads(vitals):
    """Computes min, mean, and max variability spans across all 5 vitals against clinical danger limits."""
    def make_spread(key, name, values, unit, lo, hi, limit_note, danger_low_end, warn_start, danger_start, is_danger_fn, is_warn_fn, decimals=0, inverse_spo2=False):
        if not values:
            return {
                "key": key,
                "name": name,
                "unit": unit,
                "has_data": False,
                "min_str": "–",
                "avg_str": "–",
                "max_str": "–",
                "limit_note": limit_note,
                "state": "none",
                "danger_low_end": danger_low_end,
                "warn_start": warn_start,
                "danger_start": danger_start,
                "inverse_spo2": inverse_spo2,
            }
        mn = min(values)
        mx = max(values)
        avg = sum(values) / len(values)
        fmt = (lambda x: f"{x:.{decimals}f}") if decimals else (lambda x: f"{round(x)}")
        min_pct = _clamp_pct(mn, lo, hi)
        max_pct = _clamp_pct(mx, lo, hi)
        avg_pct = _clamp_pct(avg, lo, hi)
        if is_danger_fn(mn, mx):
            state = "danger"
        elif is_warn_fn(mn, mx):
            state = "warn"
        else:
            state = "normal"
        return {
            "key": key,
            "name": name,
            "unit": unit,
            "has_data": True,
            "min_str": fmt(mn),
            "avg_str": fmt(avg),
            "max_str": fmt(mx),
            "min_pct": min_pct,
            "avg_pct": avg_pct,
            "max_pct": max_pct,
            "span_pct": round(max(1.5, max_pct - min_pct), 1),
            "limit_note": limit_note,
            "state": state,
            "danger_low_end": danger_low_end,
            "warn_start": warn_start,
            "danger_start": danger_start,
            "inverse_spo2": inverse_spo2,
        }

    sys_vals = [v.systolic for v in vitals if v.systolic is not None]
    hr_vals = [v.heart_rate for v in vitals if v.heart_rate is not None]
    spo2_vals = [float(v.oxygen_saturation) for v in vitals if v.oxygen_saturation is not None]
    temp_vals = [float(v.temperature_celsius) for v in vitals if v.temperature_celsius is not None]
    wt_vals = [float(v.weight_kg) for v in vitals if v.weight_kg is not None]

    return [
        make_spread(
            "bp", "Systolic BP", sys_vals, "mmHg", 80, 180, "Danger ≥140",
            10.0, 40.0, 60.0,
            lambda mn, mx: mx >= 140 or mn < 90,
            lambda mn, mx: mx >= 120,
            decimals=0,
        ),
        make_spread(
            "hr", "Heart rate", hr_vals, "bpm", 40, 140, "Danger <55 / >105",
            15.0, 60.0, 65.0,
            lambda mn, mx: mn < 55 or mx > 105,
            lambda mn, mx: mx > 100 or mn < 60,
            decimals=0,
        ),
        make_spread(
            "spo2", "Oxygen SpO₂", spo2_vals, "%", 85, 100, "Danger <92%",
            46.7, 100.0, 100.0,
            lambda mn, mx: mn < 92.0,
            lambda mn, mx: mn < 95.0,
            decimals=1,
            inverse_spo2=True,
        ),
        make_spread(
            "temp", "Temperature", temp_vals, "°C", 34.5, 40.0, "Danger ≥38.0°C",
            18.2, 54.5, 63.6,
            lambda mn, mx: mx >= 38.0 or mn < 35.5,
            lambda mn, mx: mx >= 37.5,
            decimals=1,
        ),
        make_spread(
            "weight", "Body weight", wt_vals, "kg", 40, 120, "Session range",
            6.0, 75.0, 88.0,
            lambda mn, mx: False,
            lambda mn, mx: (mx - mn) >= 3.0,
            decimals=1,
        ),
    ]


@login_required
def reports_view(request):
    doctor = DoctorProfile.objects.filter(user=request.user).first()
    patient = PatientProfile.objects.filter(user=request.user).first()

    if doctor is None and patient is None:
        messages.info(request, "Please set up your profile role first.")
        return redirect("home:home")

    # ==========================================
    # PATIENT CLINICAL AUDIT REPORT
    # ==========================================
    if patient is not None:
        range_key = request.GET.get("range", "all")
        if range_key not in ("7d", "30d", "all"):
            range_key = "all"

        filtered_qs, range_label = _filter_vitals_by_range(patient.vital_signs.all(), range_key)
        vitals = list(filtered_qs)
        total_readings = len(vitals)

        # CSV Export for patient audit log
        if request.GET.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="doctient-report-{patient.user.username}-{range_key}.csv"'
            writer = csv.writer(response)
            writer.writerow([
                "Recorded At", "Systolic (mmHg)", "Diastolic (mmHg)",
                "Heart Rate (bpm)", "SpO2 (%)", "Temperature (C)",
                "Weight (kg)", "Status", "Notes",
            ])
            for v in vitals:
                writer.writerow([
                    timezone.localtime(v.recorded_at).strftime("%Y-%m-%d %H:%M"),
                    v.systolic if v.systolic is not None else "",
                    v.diastolic if v.diastolic is not None else "",
                    v.heart_rate if v.heart_rate is not None else "",
                    v.oxygen_saturation if v.oxygen_saturation is not None else "",
                    v.temperature_celsius if v.temperature_celsius is not None else "",
                    v.weight_kg if v.weight_kg is not None else "",
                    v.monitoring_status or "Normal",
                    v.patient_notes or "",
                ])
            return response

        avg_sys, avg_dia, avg_hr, avg_spo2, avg_temp = None, None, None, None, None
        min_sys, max_sys = None, None
        pulse_pressure = None
        mean_arterial_pressure = None
        map_state = "none"
        pp_state = "none"
        bp_classification = "No data"
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
                mean_arterial_pressure = round(avg_dia + (pulse_pressure / 3.0))
                if mean_arterial_pressure >= 110 or mean_arterial_pressure < 65:
                    map_state = "danger"
                elif mean_arterial_pressure > 100 or mean_arterial_pressure < 70:
                    map_state = "warn"
                else:
                    map_state = "normal"

                if pulse_pressure >= 60 or pulse_pressure < 25:
                    pp_state = "danger"
                elif pulse_pressure > 50 or pulse_pressure < 30:
                    pp_state = "warn"
                else:
                    pp_state = "normal"

                if avg_sys < 120 and avg_dia < 80:
                    bp_classification = "Normal"
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

        # BMI (from latest overall vital or profile)
        all_latest = patient.vital_signs.first()
        latest_vital = vitals[0] if vitals else all_latest
        current_weight = latest_vital.weight_kg if latest_vital and latest_vital.weight_kg else patient.weight_kg
        bmi_value, bmi_category = _calculate_bmi(current_weight, patient.height_cm)
        bmi_marker_pct = _clamp_pct(bmi_value, 15.0, 35.0) if bmi_value is not None else None

        # Medication Compliance (overall + per-regimen bullet rows vs 85% target)
        medications = list(patient.medications.all())
        total_med_logs = MedicationLog.objects.filter(medication__patient=patient).count()
        taken_med_logs = MedicationLog.objects.filter(medication__patient=patient, is_taken=True).count()
        adherence_rate = (
            round((taken_med_logs / total_med_logs) * 100) if total_med_logs > 0 else 100
        )
        adherence_style = f"width: {adherence_rate}%;"

        med_compliance_bullet = []
        for m in medications:
            m_total = m.logs.count()
            m_taken = m.logs.filter(is_taken=True).count()
            m_rate = round(m_taken / m_total, 3) if m_total > 0 else 0.0
            m.taken_logs = m_taken
            m.total_logs = m_total
            m.adherence_pct = round(m_rate * 100) if m_total > 0 else 0
            med_compliance_bullet.append({
                "label": m.medication,
                "value": m_rate,
                "target": 0.85,
                "tolerance": 0.05,
            })

        # Reports-exclusive analytics: Risk Distribution & Min-Mean-Max Clinical Spreads
        risk_distribution = _build_risk_distribution(vitals)
        danger_session_count = next((r["count"] for r in risk_distribution if r["key"] == "danger"), 0)
        normal_session_pct = next((r["pct"] for r in risk_distribution if r["key"] == "normal"), 0)
        vital_spreads = _build_vital_spreads(vitals)

        avg_bp_pct = _clamp_pct(avg_sys, 80, 180) if avg_sys is not None else None
        map_marker_pct = _clamp_pct(mean_arterial_pressure, 55, 130) if mean_arterial_pressure is not None else None
        pp_marker_pct = _clamp_pct(pulse_pressure, 20, 80) if pulse_pressure is not None else None

        return render(request, "reports/reports.html", {
            "is_patient": True,
            "patient": patient,
            "range_key": range_key,
            "range_label": range_label,
            "total_readings": total_readings,
            "avg_sys": avg_sys,
            "avg_dia": avg_dia,
            "min_sys": min_sys,
            "max_sys": max_sys,
            "pulse_pressure": pulse_pressure,
            "mean_arterial_pressure": mean_arterial_pressure,
            "map_state": map_state,
            "pp_state": pp_state,
            "bp_classification": bp_classification,
            "bp_badge": bp_badge,
            "avg_hr": avg_hr,
            "avg_spo2": avg_spo2,
            "avg_temp": avg_temp,
            "avg_bp_pct": avg_bp_pct,
            "map_marker_pct": map_marker_pct,
            "pp_marker_pct": pp_marker_pct,
            "current_weight": current_weight,
            "bmi_value": bmi_value,
            "bmi_category": bmi_category,
            "bmi_marker_pct": bmi_marker_pct,
            "medications": medications,
            "adherence_rate": adherence_rate,
            "adherence_style": adherence_style,
            "med_compliance_bullet": med_compliance_bullet,
            "risk_distribution": risk_distribution,
            "danger_session_count": danger_session_count,
            "normal_session_pct": normal_session_pct,
            "vital_spreads": vital_spreads,
            "trend_readings": vitals,
            "latest_vital": latest_vital,
        })

    # ==========================================
    # DOCTOR COHORT ANALYTICS REPORT
    # ==========================================
    risk_filter = request.GET.get("risk", "all")
    if risk_filter not in ("all", "high", "elevated", "stable"):
        risk_filter = "all"

    patients = list(
        PatientProfile.objects.raw(
            """
            SELECT p.id, p.user_id, p.full_name, p.date_of_birth, p.gender, p.contact_no, p.address
            FROM patient_profiles p
            WHERE p.id IN (
                SELECT c.patient_id
                FROM doctor_patient_connections c
                WHERE c.doctor_id = %s
            )
            ORDER BY p.full_name ASC
            """,
            [doctor.id],
        )
    )
    patient_ids = [p.id for p in patients]

    triage_alerts = []
    elevated_patients = []
    stable_patients = []
    normal_patients = []
    all_sys = []
    all_dia = []
    total_active_meds = 0
    cohort_adherence_bullet = []

    for p in patients:
        latest = p.vital_signs.first()
        p.latest_vital = latest
        p.active_meds = list(p.medications.filter(status="active"))
        p.total_meds = len(p.active_meds)
        total_active_meds += Medication.objects.filter(doctor=doctor, patient=p, status="active").count()

        p_total_logs = MedicationLog.objects.filter(medication__patient=p).count()
        p_taken_logs = MedicationLog.objects.filter(medication__patient=p, is_taken=True).count()
        p_rate = round(p_taken_logs / p_total_logs, 3) if p_total_logs > 0 else 0.0
        p.adherence_pct = round(p_rate * 100) if p_total_logs > 0 else None
        cohort_adherence_bullet.append({
            "label": p.full_name,
            "value": p_rate,
            "target": 0.85,
            "tolerance": 0.05,
        })

        if latest:
            if latest.systolic:
                all_sys.append(latest.systolic)
            if latest.diastolic:
                all_dia.append(latest.diastolic)

        p.bp_marker_pct = _clamp_pct(latest.systolic, 80, 180) if latest and latest.systolic else None

        if latest and (
            (latest.systolic and latest.systolic >= 140)
            or (latest.diastolic and latest.diastolic >= 90)
            or (latest.oxygen_saturation and float(latest.oxygen_saturation) < 92)
        ):
            p.triage_key = "high"
            p.triage_level = "High priority"
            p.triage_badge = "badge-danger"
            triage_alerts.append(p)
        elif latest and (
            (latest.systolic and latest.systolic >= 130)
            or (latest.diastolic and latest.diastolic >= 80)
        ):
            p.triage_key = "elevated"
            p.triage_level = "Elevated"
            p.triage_badge = "badge-warning"
            elevated_patients.append(p)
            normal_patients.append(p)
        else:
            p.triage_key = "stable"
            p.triage_level = "Stable"
            p.triage_badge = "badge-success"
            stable_patients.append(p)
            normal_patients.append(p)

    # Filtered triage rows (High priority always sorted first)
    ordered_cohort = triage_alerts + elevated_patients + stable_patients
    if risk_filter == "high":
        filtered_cohort = triage_alerts
    elif risk_filter == "elevated":
        filtered_cohort = elevated_patients
    elif risk_filter == "stable":
        filtered_cohort = stable_patients
    else:
        filtered_cohort = ordered_cohort

    # Doctor CSV Export
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="doctient-cohort-report-{risk_filter}.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Patient Name", "Username", "Latest BP (mmHg)", "Heart Rate (bpm)",
            "SpO2 (%)", "Active Meds", "Triage Risk", "Last Reading",
        ])
        for p in filtered_cohort:
            lv = p.latest_vital
            bp_str = f"{lv.systolic}/{lv.diastolic}" if lv and lv.systolic else ""
            writer.writerow([
                p.full_name,
                p.user.username,
                bp_str,
                lv.heart_rate if lv and lv.heart_rate else "",
                lv.oxygen_saturation if lv and lv.oxygen_saturation else "",
                p.total_meds,
                p.triage_level,
                timezone.localtime(lv.recorded_at).strftime("%Y-%m-%d %H:%M") if lv else "",
            ])
        return response

    total_cohort = len(patients)
    cohort_avg_sys = round(sum(all_sys) / len(all_sys)) if all_sys else None
    cohort_avg_dia = round(sum(all_dia) / len(all_dia)) if all_dia else None
    controlled_count = len(stable_patients)
    controlled_pct = round((controlled_count / total_cohort) * 100) if total_cohort else 0

    cohort_risk_breakdown = [
        {
            "key": "stable",
            "label": "Stable",
            "tone": "pos",
            "count": len(stable_patients),
            "pct": round((len(stable_patients) / total_cohort) * 100) if total_cohort else 0,
            "criteria": "Within safe clinical thresholds",
        },
        {
            "key": "elevated",
            "label": "Elevated",
            "tone": "warn",
            "count": len(elevated_patients),
            "pct": round((len(elevated_patients) / total_cohort) * 100) if total_cohort else 0,
            "criteria": "BP 130–139 / 80–89 mmHg",
        },
        {
            "key": "high",
            "label": "High priority",
            "tone": "neg",
            "count": len(triage_alerts),
            "pct": round((len(triage_alerts) / total_cohort) * 100) if total_cohort else 0,
            "criteria": "BP ≥140/90 or SpO₂ <92%",
        },
    ]

    # Per-patient drill-down
    detail_patient = None
    detail_vitals = []
    detail_medications = []
    detail_adherence = 100
    detail_connection = None
    detail_gauges = []
    detail_chart_data = None
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
                detail_gauges = build_clinical_vital_gauges(
                    detail_vitals[0] if detail_vitals else None,
                    detail_vitals,
                    patient=detail_patient,
                )
                detail_chart_data = build_vitals_chart_payload(detail_vitals)
        except PatientProfile.DoesNotExist:
            detail_patient = None

    doctor_notes = list(DoctorNote.objects.filter(doctor=doctor).order_by("-id")[:20])

    return render(request, "reports/reports.html", {
        "is_doctor": True,
        "doctor": doctor,
        "risk_filter": risk_filter,
        "total_cohort": total_cohort,
        "triage_alerts": triage_alerts,
        "elevated_patients": elevated_patients,
        "stable_patients": stable_patients,
        "normal_patients": normal_patients,
        "filtered_cohort": filtered_cohort,
        "patients": patients,
        "cohort_avg_sys": cohort_avg_sys,
        "cohort_avg_dia": cohort_avg_dia,
        "controlled_count": controlled_count,
        "controlled_pct": controlled_pct,
        "total_active_meds": total_active_meds,
        "cohort_risk_breakdown": cohort_risk_breakdown,
        "cohort_adherence_bullet": cohort_adherence_bullet,
        "detail_patient": detail_patient,
        "detail_vitals": detail_vitals,
        "detail_medications": detail_medications,
        "detail_adherence": detail_adherence,
        "detail_connection": detail_connection,
        "detail_gauges": detail_gauges,
        "detail_chart_data": detail_chart_data,
        "doctor_notes": doctor_notes,
    })
