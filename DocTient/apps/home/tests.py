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
