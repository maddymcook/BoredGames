from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Avg


class Listing(models.Model):
    LISTING_TYPE_SWAP = "swap"
    LISTING_TYPE_BUY = "buy"
    LISTING_TYPE_CHOICES = (
        (LISTING_TYPE_SWAP, "Swap"),
        (LISTING_TYPE_BUY, "Buy"),
    )

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    APPROVAL_STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    )

    owner = models.ForeignKey(
        "accounts.UserAccount",
        on_delete=models.CASCADE,
        related_name="listings",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="listing_images/", null=True, blank=True)
    listing_type = models.CharField(max_length=10, choices=LISTING_TYPE_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    iso_text = models.TextField(null=True, blank=True)
    tags = models.ManyToManyField("accounts.GenreTag", blank=True, related_name="listings")

    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    approved_by = models.ForeignKey(
        "accounts.UserAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_listings",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

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

    @property
    def average_rating(self):
        value = self.ratings.aggregate(avg=Avg("score"))["avg"]
        return round(value or 0, 2)

    @property
    def rating_count(self):
        return self.ratings.count()

    def __str__(self):
        return f"{self.title} ({self.listing_type})"


class ListingRating(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    user = models.ForeignKey(
        "accounts.UserAccount",
        on_delete=models.CASCADE,
        related_name="listing_ratings",
    )
    score = models.PositiveSmallIntegerField()
    review = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("listing", "user")
        ordering = ["-created_at"]

    def clean(self):
        if self.score < 1 or self.score > 5:
            raise ValidationError({"score": "Rating must be between 1 and 5."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.listing.title} - {self.user.username} - {self.score}"