from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.clinic.models import DoctorProfile, Message, PatientProfile


class MessagingViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient_user = User.objects.create_user(username="pat1", password="Password123!")
        self.patient = PatientProfile.objects.create(user=self.patient_user, full_name="Patient One")

        self.doctor_user = User.objects.create_user(username="doc1", password="Password123!")
        self.doctor = DoctorProfile.objects.create(user=self.doctor_user, full_name="Dr. One", med_specialty="Pediatrics")

    def test_send_message_from_patient_to_doctor(self):
        self.client.login(username="pat1", password="Password123!")
        response = self.client.post(reverse("messages:messages"), {
            "recipient": "doc1",
            "content": "Hello doctor, asking about my vitals"
        })
        self.assertEqual(response.status_code, 302)
        msg = Message.objects.filter(sender=self.patient_user, recipient=self.doctor_user).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.content, "Hello doctor, asking about my vitals")

    def test_messaging_between_same_role_prevented(self):
        pat2_user = User.objects.create_user(username="pat2", password="Password123!")
        PatientProfile.objects.create(user=pat2_user, full_name="Patient Two")

        self.client.login(username="pat1", password="Password123!")
        response = self.client.post(reverse("messages:messages"), {
            "recipient": "pat2",
            "content": "Hi other patient"
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Message.objects.filter(sender=self.patient_user, recipient=pat2_user).count(), 0)

