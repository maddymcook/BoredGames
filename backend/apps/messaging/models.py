from django.db import models


class Message(models.Model):
    sender = models.ForeignKey(
        "accounts.UserAccount",
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    recipient = models.ForeignKey(
        "accounts.UserAccount",
        on_delete=models.CASCADE,
        related_name="received_messages",
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Message {self.id} from {self.sender_id} to {self.recipient_id}"
