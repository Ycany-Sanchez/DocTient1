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

