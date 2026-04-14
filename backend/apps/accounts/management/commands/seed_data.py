from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.accounts.models import UserAccount
from apps.listings.models import Listing
from apps.messaging.models import Message


class Command(BaseCommand):
    help = "Seed sample users, listings, and messages for local frontend testing."

    def handle(self, *args, **options):
        user_one, _ = UserAccount.objects.get_or_create(
            email="sample1@example.com",
            defaults={"username": "sample1", "is_admin": False},
        )
        user_one.set_password("password123")
        user_one.save()

        user_two, _ = UserAccount.objects.get_or_create(
            email="sample2@example.com",
            defaults={"username": "sample2", "is_admin": False},
        )
        user_two.set_password("password123")
        user_two.save()

        buy_listing, _ = Listing.objects.get_or_create(
            owner=user_one,
            title="Catan",
            defaults={
                "description": "Gently used Catan base game.",
                "listing_type": Listing.LISTING_TYPE_BUY,
                "price": Decimal("25.00"),
            },
        )

        swap_listing, _ = Listing.objects.get_or_create(
            owner=user_two,
            title="Wingspan",
            defaults={
                "description": "Looking to swap for family strategy games.",
                "listing_type": Listing.LISTING_TYPE_SWAP,
                "iso_text": "Ticket to Ride",
            },
        )

        Message.objects.get_or_create(
            sender=user_two,
            recipient=user_one,
            listing=buy_listing,
            content="Hi! Is this still available?",
        )
        Message.objects.get_or_create(
            sender=user_one,
            recipient=user_two,
            listing=swap_listing,
            content="Would you trade for Azul?",
        )

        self.stdout.write(self.style.SUCCESS("Sample data created successfully."))
