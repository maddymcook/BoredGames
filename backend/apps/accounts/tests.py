from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

UserAccount = get_user_model()


class UserApiTests(APITestCase):
    def test_user_signup(self):
        response = self.client.post(
            "/api/users/",
            {
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "password123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)

    def test_jwt_token_obtain(self):
        UserAccount.objects.create_user(
            email="auth@example.com",
            username="authuser",
            password="password123",
        )
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "auth@example.com", "password": "password123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
