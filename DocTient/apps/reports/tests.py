from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.clinic.models import (
    DoctorPatientConnection,
    DoctorProfile,
    PatientProfile,
    VitalSign,
    Medication,
    MedicationLog,
)


class ReportsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create Patient
        self.patient_user = User.objects.create_user(
            username="rep_patient", password="Password123!"
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            full_name="Reports Patient",
            height_cm=170,
            weight_kg=65.0,
        )

        # Create Doctor
        self.doctor_user = User.objects.create_user(
            username="rep_doctor", password="Password123!"
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            full_name="Dr. Analytics",
            med_specialty="Cardiology",
        )

        DoctorPatientConnection.objects.create(doctor=self.doctor, patient=self.patient)

        # Create Vital Signs
        VitalSign.objects.create(
            patient=self.patient,
            systolic=120,
            diastolic=80,
            heart_rate=72,
            oxygen_saturation=98.5,
            temperature_celsius=36.6,
            weight_kg=65.0,
            monitoring_status="Normal",
        )
        VitalSign.objects.create(
            patient=self.patient,
            systolic=118,
            diastolic=78,
            heart_rate=70,
            oxygen_saturation=99.0,
            temperature_celsius=36.5,
            weight_kg=65.2,
            monitoring_status="Normal",
        )

    def test_unauthenticated_redirects(self):
        response = self.client.get(reverse("reports:reports"))
        self.assertEqual(response.status_code, 302)

    def test_patient_reports_view_renders(self):
        self.client.login(username="rep_patient", password="Password123!")
        response = self.client.get(reverse("reports:reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reports Patient")
        self.assertContains(response, "Mean Blood Pressure")
        # 120 and 118 avg is 119
        self.assertContains(response, "119")

    def test_doctor_cohort_report_renders(self):
        self.client.login(username="rep_doctor", password="Password123!")
        response = self.client.get(reverse("reports:reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Patient Cohort Triage Overview")
        self.assertContains(response, "Reports Patient")

    def test_patient_report_computes_risk_distribution_map_and_spreads(self):
        # Add one hypertensive reading so distribution covers multiple zones
        VitalSign.objects.create(
            patient=self.patient,
            systolic=148,
            diastolic=94,
            heart_rate=88,
            oxygen_saturation=97.0,
            temperature_celsius=36.9,
            weight_kg=65.5,
            monitoring_status="Stage 2 HTN",
        )
        self.client.login(username="rep_patient", password="Password123!")
        response = self.client.get(reverse("reports:reports"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["mean_arterial_pressure"])
        dist = response.context["risk_distribution"]
        self.assertEqual(sum(r["count"] for r in dist), response.context["total_readings"])
        danger_row = next(r for r in dist if r["key"] == "danger")
        self.assertEqual(danger_row["count"], 1)
        bp_spread = next(s for s in response.context["vital_spreads"] if s["key"] == "bp")
        self.assertEqual(bp_spread["min_str"], "118")
        self.assertEqual(bp_spread["max_str"], "148")
        self.assertEqual(bp_spread["state"], "danger")

    def test_patient_report_timeframe_filter_and_csv_export(self):
        from datetime import timedelta
        from django.utils import timezone

        old_v = VitalSign.objects.create(
            patient=self.patient,
            systolic=155,
            diastolic=98,
            monitoring_status="Stage 2 HTN",
        )
        VitalSign.objects.filter(id=old_v.id).update(
            recorded_at=timezone.now() - timedelta(days=45)
        )
        self.client.login(username="rep_patient", password="Password123!")

        r_7d = self.client.get(reverse("reports:reports") + "?range=7d")
        self.assertEqual(r_7d.status_code, 200)
        self.assertEqual(r_7d.context["total_readings"], 2)

        r_all = self.client.get(reverse("reports:reports") + "?range=all")
        self.assertEqual(r_all.context["total_readings"], 3)

        r_csv = self.client.get(reverse("reports:reports") + "?range=7d&export=csv")
        self.assertEqual(r_csv.status_code, 200)
        self.assertIn("text/csv", r_csv["Content-Type"])
        body = r_csv.content.decode("utf-8")
        self.assertIn("Systolic (mmHg)", body)
        self.assertIn("120,80", body)

    def test_doctor_cohort_risk_filter_and_csv_export(self):
        self.client.login(username="rep_doctor", password="Password123!")
        r_high = self.client.get(reverse("reports:reports") + "?risk=high")
        self.assertEqual(r_high.status_code, 200)
        self.assertEqual(len(r_high.context["filtered_cohort"]), 0)

        r_csv = self.client.get(reverse("reports:reports") + "?risk=all&export=csv")
        self.assertEqual(r_csv.status_code, 200)
        self.assertIn("text/csv", r_csv["Content-Type"])
        self.assertIn("Reports Patient", r_csv.content.decode("utf-8"))


