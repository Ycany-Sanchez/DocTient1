from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.clinic.models import DoctorProfile, PatientProfile


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_page_renders(self):
        response = self.client.get(reverse("register:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Account")

    def test_register_patient_creates_account(self):
        response = self.client.post(
            reverse("register:register"),
            {
                "username": "new_patient",
                "password": "Password123!",
                "full_name": "New Patient",
                "role": "patient",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:login"))
        user = User.objects.filter(username="new_patient").first()
        self.assertIsNotNone(user)
        patient = PatientProfile.objects.filter(user=user).first()
        self.assertIsNotNone(patient)
        self.assertEqual(patient.full_name, "New Patient")

    def test_register_doctor_creates_account(self):
        response = self.client.post(
            reverse("register:register"),
            {
                "username": "new_doctor",
                "password": "Password123!",
                "full_name": "Dr. Specialist",
                "role": "doctor",
                "med_specialty": "Neurology",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:login"))
        user = User.objects.filter(username="new_doctor").first()
        self.assertIsNotNone(user)
        doctor = DoctorProfile.objects.filter(user=user).first()
        self.assertIsNotNone(doctor)
        self.assertEqual(doctor.med_specialty, "Neurology")

    def test_register_existing_username_fails(self):
        User.objects.create_user(username="existing_user", password="Password123!")
        response = self.client.post(
            reverse("register:register"),
            {
                "username": "existing_user",
                "password": "Password123!",
                "role": "patient",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username already exists.")

    def test_register_missing_fields_fails(self):
        response = self.client.post(
            reverse("register:register"),
            {
                "username": "",
                "password": "",
                "role": "patient",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username and password are required.")
