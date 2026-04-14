from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Listing

UserAccount = get_user_model()


class ListingModelTests(APITestCase):
    def setUp(self):
        self.user = UserAccount.objects.create_user(
            email="owner@example.com",
            username="owner",
            password="password123",
        )

    def test_buy_listing_requires_price(self):
        listing = Listing(
            owner=self.user,
            title="Catan",
            listing_type=Listing.LISTING_TYPE_BUY,
            price=None,
        )
        with self.assertRaises(ValidationError):
            listing.full_clean()

    def test_swap_listing_requires_iso(self):
        listing = Listing(
            owner=self.user,
            title="Ticket to Ride",
            listing_type=Listing.LISTING_TYPE_SWAP,
            iso_text="",
        )
        with self.assertRaises(ValidationError):
            listing.full_clean()

    def test_buy_listing_clears_iso(self):
        listing = Listing.objects.create(
            owner=self.user,
            title="Azul",
            listing_type=Listing.LISTING_TYPE_BUY,
            price=Decimal("20.00"),
            iso_text="Unused text",
        )
        self.assertIsNone(listing.iso_text)


class ListingApiTests(APITestCase):
    def setUp(self):
        self.user = UserAccount.objects.create_user(
            email="owner2@example.com",
            username="owner2",
            password="password123",
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "owner2@example.com", "password": "password123"},
            format="json",
        )
        self.access_token = token_response.data["access"]

    def test_listing_create_and_filter(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        create_response = self.client.post(
            "/api/listings/",
            {
                "owner": self.user.id,
                "title": "Root",
                "description": "Great game",
                "listing_type": "swap",
                "iso_text": "Wingspan",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)

        list_response = self.client.get("/api/listings/?listing_type=swap")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
