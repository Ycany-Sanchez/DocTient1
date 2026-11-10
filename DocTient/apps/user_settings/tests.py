from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.user_settings.models import UserSettings


class SettingsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="settings_tester", password="Password123!"
        )

    def test_settings_requires_login(self):
        response = self.client.get(reverse("user_settings:settings"))
        self.assertEqual(response.status_code, 302)

    def test_settings_page_renders_for_logged_in_user(self):
        self.client.login(username="settings_tester", password="Password123!")
        response = self.client.get(reverse("user_settings:settings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dark Theme Display")
        self.assertContains(response, "Critical Telemetry Alerts")

    def test_settings_toggle_preferences(self):
        self.client.login(username="settings_tester", password="Password123!")
        response = self.client.post(
            reverse("user_settings:settings"),
            {
                "dark_mode": "on",
                "email_notifications": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        settings = UserSettings.objects.get(user=self.user)
        self.assertTrue(settings.dark_mode)
        self.assertTrue(settings.email_notifications)

        # Toggle off
        response = self.client.post(reverse("user_settings:settings"), {})
        self.assertEqual(response.status_code, 302)
        settings.refresh_from_db()
        self.assertFalse(settings.dark_mode)
        self.assertFalse(settings.email_notifications)
