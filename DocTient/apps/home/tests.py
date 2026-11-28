from decimal import Decimal
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


class DocTientDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create Patient
        self.patient_user = User.objects.create_user(
            username="test_patient", password="Password123!"
        )
        self.patient_profile = PatientProfile.objects.create(
            user=self.patient_user,
            full_name="Test Patient"
        )

        # Create Doctor
        self.doctor_user = User.objects.create_user(
            username="test_doctor", password="Password123!"
        )
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor_user,
            full_name="Dr. Test",
            med_specialty="Cardiology"
        )

        # Connect Doctor and Patient
        self.conn = DoctorPatientConnection.objects.create(
            doctor=self.doctor_profile,
            patient=self.patient_profile,
            observations="Stable vitals",
            recommendations="Routine checkups"
        )

        # Create Medication
        self.med = Medication.objects.create(
            patient=self.patient_profile,
            doctor=self.doctor_profile,
            medication="Lisinopril 10mg",
            dosage="1 Tablet",
            frequency="Daily",
            status="active"
        )

    def test_patient_dashboard_renders(self):
        self.client.login(username="test_patient", password="Password123!")
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Patient")
        self.assertContains(response, "Lisinopril 10mg")

    def test_patient_can_log_vital(self):
        self.client.login(username="test_patient", password="Password123!")
        response = self.client.post(reverse("home:home"), {
            "action": "log_vital",
            "systolic": "120",
            "diastolic": "80",
            "heart_rate": "72",
            "temperature_celsius": "36.6",
            "oxygen_saturation": "98.5",
            "weight_kg": "65.0",
            "patient_notes": "Morning checkup"
        })
        self.assertEqual(response.status_code, 302)
        vital = VitalSign.objects.filter(patient=self.patient_profile).first()
        self.assertIsNotNone(vital)
        self.assertEqual(vital.systolic, 120)
        self.assertEqual(vital.diastolic, 80)
        self.assertEqual(vital.monitoring_status, "Stage 1 HTN")

    def test_patient_can_mark_medication_taken(self):
        self.client.login(username="test_patient", password="Password123!")
        response = self.client.post(reverse("home:home"), {
            "action": "mark_medication_taken",
            "medication_id": str(self.med.id)
        })
        self.assertEqual(response.status_code, 302)
        log = MedicationLog.objects.filter(medication=self.med).first()
        self.assertIsNotNone(log)
        self.assertTrue(log.is_taken)

    def test_doctor_dashboard_renders(self):
        self.client.login(username="test_doctor", password="Password123!")
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dr. Test")
        self.assertContains(response, "Test Patient")

    def test_doctor_can_record_vitals_for_patient(self):
        self.client.login(username="test_doctor", password="Password123!")
        response = self.client.post(reverse("home:home"), {
            "action": "record_patient_vitals",
            "patient_id": str(self.patient_profile.id),
            "systolic": "118",
            "diastolic": "78",
            "heart_rate": "70",
            "temperature_celsius": "36.5",
            "oxygen_saturation": "99.0",
            "weight_kg": "64.8",
            "monitoring_status": "Normal",
            "patient_notes": "Clinical telemetry check"
        })
        self.assertEqual(response.status_code, 302)
        vital = VitalSign.objects.filter(patient=self.patient_profile).first()
        self.assertIsNotNone(vital)
        self.assertEqual(vital.systolic, 118)
        self.assertEqual(vital.monitoring_status, "Normal")

    def test_patient_ajax_toggle_medication_without_refresh(self):
        self.client.login(username="test_patient", password="Password123!")
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
        # Mark taken via AJAX -> returns JSON 200 (no redirect)
        resp = self.client.post(
            reverse("home:home"),
            {"action": "toggle_medication_taken", "medication_id": str(self.med.id)},
            **headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["taken_today"])
        self.assertEqual(data["taken_today_count"], 1)
        self.assertEqual(data["today_adherence_pct"], 100)

        # Toggle off (undo) via AJAX -> removes today's log without refresh
        resp2 = self.client.post(
            reverse("home:home"),
            {"action": "toggle_medication_taken", "medication_id": str(self.med.id)},
            **headers,
        )
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertTrue(data2["ok"])
        self.assertFalse(data2["taken_today"])
        self.assertEqual(data2["taken_today_count"], 0)
        self.assertEqual(data2["today_adherence_pct"], 0)

    def test_patient_dashboard_computes_clinical_danger_gauges(self):
        VitalSign.objects.create(
            patient=self.patient_profile,
            systolic=152,
            diastolic=95,
            heart_rate=112,
            oxygen_saturation=Decimal("90.5"),
            temperature_celsius=Decimal("38.4"),
            weight_kg=Decimal("70.0"),
            monitoring_status="Stage 2 HTN",
        )
        self.client.login(username="test_patient", password="Password123!")
        resp = self.client.get(reverse("home:home"))
        self.assertEqual(resp.status_code, 200)
        gauges = {g["key"]: g for g in resp.context["vital_gauges"]}
        self.assertEqual(gauges["bp"]["state"], "danger")
        self.assertEqual(gauges["hr"]["state"], "danger")
        self.assertEqual(gauges["spo2"]["state"], "danger")
        self.assertEqual(gauges["temp"]["state"], "danger")

    def test_doctor_notes_are_scoped_to_selected_patient(self):
        other_user = User.objects.create_user(username="other_pat", password="Password123!")
        other_pat = PatientProfile.objects.create(user=other_user, full_name="Other Patient")
        DoctorPatientConnection.objects.create(doctor=self.doctor_profile, patient=other_pat)

        self.client.login(username="test_doctor", password="Password123!")
        self.client.post(reverse("home:home"), {
            "action": "update_clinical_note",
            "patient_id": str(self.patient_profile.id),
            "observations": "Note specifically for Test Patient",
            "recommendations": "Keep hydrated",
        })
        resp = self.client.get(reverse("home:home") + f"?patient_id={other_pat.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Note specifically for Test Patient")

        resp2 = self.client.get(reverse("home:home") + f"?patient_id={self.patient_profile.id}")
        self.assertContains(resp2, "Note specifically for Test Patient")

    def test_doctor_can_prescribe_with_schedule_and_edit_medication(self):
        self.client.login(username="test_doctor", password="Password123!")
        self.client.post(reverse("home:home"), {
            "action": "prescribe_medication",
            "patient_id": str(self.patient_profile.id),
            "medication": "Amlodipine",
            "dosage": "5 mg",
            "frequency": "Once daily",
            "scheduled_time": "08:00",
            "start_date": "2026-11-28",
        })
        med = Medication.objects.filter(patient=self.patient_profile, medication="Amlodipine").first()
        self.assertIsNotNone(med)
        self.assertEqual(med.scheduled_time.strftime("%H:%M"), "08:00")
        self.assertEqual(str(med.start_date), "2026-11-28")

        self.client.post(reverse("home:home"), {
            "action": "edit_medication",
            "patient_id": str(self.patient_profile.id),
            "medication_id": str(med.id),
            "dosage": "10 mg",
            "frequency": "Twice daily",
            "scheduled_time": "20:00",
        })
        med.refresh_from_db()
        self.assertEqual(med.dosage, "10 mg")
        self.assertEqual(med.frequency, "Twice daily")
        self.assertEqual(med.scheduled_time.strftime("%H:%M"), "20:00")

