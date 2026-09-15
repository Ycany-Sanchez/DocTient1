from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthenticationFlowTests(TestCase):
    def test_home_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse("home"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('home')}",
        )

    def test_register_logs_user_in_and_opens_home(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "demo_patient",
                "email": "patient@example.com",
                "password1": "Strong-password-123",
                "password2": "Strong-password-123",
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertContains(self.client.get(reverse("home")), "HOME SCREEN")
        self.assertTrue(User.objects.filter(username="demo_patient").exists())

    def test_login_and_logout_complete_the_navigation_flow(self):
        User.objects.create_user(
            username="demo_doctor",
            password="Strong-password-123",
        )

        login_response = self.client.post(
            reverse("login"),
            {
                "username": "demo_doctor",
                "password": "Strong-password-123",
            },
        )
        self.assertRedirects(login_response, reverse("home"))

        logout_response = self.client.post(reverse("logout"))
        self.assertRedirects(logout_response, reverse("login"))