from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.clinic.models import DoctorProfile, PatientProfile
from apps.user_profile.models import Profile


class ProfileViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient_user = User.objects.create_user(
            username="pat_user", password="Password123!"
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            full_name="Patient Sample",
        )

        self.doctor_user = User.objects.create_user(
            username="doc_user", password="Password123!"
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            full_name="Dr. Sample",
            med_specialty="Pediatrics",
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile:profile"))
        self.assertEqual(response.status_code, 302)

    def test_patient_can_update_profile(self):
        self.client.login(username="pat_user", password="Password123!")
        response = self.client.post(
            reverse("profile:profile"),
            {
                "full_name": "Updated Patient Name",
                "contact_no": "+63 917 111 2222",
                "emergency_contact_no": "+63 918 333 4444",
                "gender": "Female",
                "address": "Makati City",
                "bio": "Asthmatic condition under management",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.full_name, "Updated Patient Name")
        self.assertEqual(self.patient.gender, "Female")
        self.assertEqual(self.patient.contact_no, "+63 917 111 2222")
        profile = Profile.objects.filter(user=self.patient_user).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.bio, "Asthmatic condition under management")

    def test_doctor_can_update_profile(self):
        self.client.login(username="doc_user", password="Password123!")
        response = self.client.post(
            reverse("profile:profile"),
            {
                "full_name": "Dr. Updated Specialist",
                "med_specialty": "Cardiothoracic Surgery",
                "contact_no": "+63 2 8999 8888",
                "bio": "Fellow, Philippine College of Physicians",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.full_name, "Dr. Updated Specialist")
        self.assertEqual(self.doctor.med_specialty, "Cardiothoracic Surgery")
