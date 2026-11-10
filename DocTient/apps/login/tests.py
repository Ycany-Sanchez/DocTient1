from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="auth_tester", password="Password123!"
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("login:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign In")

    def test_login_valid_credentials(self):
        response = self.client.post(
            reverse("login:login"),
            {"username": "auth_tester", "password": "Password123!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home:home"))

    def test_login_invalid_credentials(self):
        response = self.client.post(
            reverse("login:login"),
            {"username": "auth_tester", "password": "WrongPassword!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password.")

    def test_authenticated_user_redirects_away(self):
        self.client.login(username="auth_tester", password="Password123!")
        response = self.client.get(reverse("login:login"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home:home"))
