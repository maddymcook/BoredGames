from django.db import models
from django.core.exceptions import ValidationError


class Listing(models.Model):
    LISTING_TYPE_SWAP = "swap"
    LISTING_TYPE_BUY = "buy"
    LISTING_TYPE_CHOICES = (
        (LISTING_TYPE_SWAP, "Swap"),
        (LISTING_TYPE_BUY, "Buy"),
    )

    owner = models.ForeignKey(
        "accounts.UserAccount",
        on_delete=models.CASCADE,
        related_name="listings",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    listing_type = models.CharField(max_length=10, choices=LISTING_TYPE_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    iso_text = models.TextField(null=True, blank=True)
    tags = models.ManyToManyField("accounts.GenreTag", blank=True, related_name="listings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.listing_type == self.LISTING_TYPE_BUY:
            if self.price is None:
                raise ValidationError({"price": "Price is required for buy listings."})
            if self.price < 0:
                raise ValidationError({"price": "Price cannot be negative."})
            self.iso_text = None

        if self.listing_type == self.LISTING_TYPE_SWAP:
            if not self.iso_text:
                raise ValidationError({"iso_text": "ISO text is required for swap listings."})
            self.price = None

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.listing_type})"
