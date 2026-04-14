from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.messaging.models import Message

UserAccount = get_user_model()


class MessageApiTests(APITestCase):
    def setUp(self):
        self.user_a = UserAccount.objects.create_user(
            email="a@example.com", username="usera", password="password123"
        )
        self.user_b = UserAccount.objects.create_user(
            email="b@example.com", username="userb", password="password123"
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "a@example.com", "password": "password123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

    def test_send_message(self):
        response = self.client.post(
            "/api/messages/",
            {"sender": self.user_a.id, "recipient": self.user_b.id, "content": "Hi there"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Message.objects.count(), 1)

    def test_prevent_self_message(self):
        response = self.client.post(
            "/api/messages/",
            {"sender": self.user_a.id, "recipient": self.user_a.id, "content": "Hi self"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
