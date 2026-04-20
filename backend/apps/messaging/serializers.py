from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "recipient",
            "listing",
            "content",
            "is_read",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("is_read", "created_at", "updated_at")

    def validate(self, attrs):
        sender = attrs.get("sender", getattr(self.instance, "sender", None))
        recipient = attrs.get("recipient", getattr(self.instance, "recipient", None))
        if sender and recipient and sender == recipient:
            raise serializers.ValidationError("Sender and recipient cannot be the same user.")
        return attrs
