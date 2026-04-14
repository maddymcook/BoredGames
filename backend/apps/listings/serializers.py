from rest_framework import serializers

from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = (
            "id",
            "owner",
            "title",
            "description",
            "listing_type",
            "price",
            "iso_text",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate(self, attrs):
        listing_type = attrs.get("listing_type", getattr(self.instance, "listing_type", None))
        price = attrs.get("price", getattr(self.instance, "price", None))
        iso_text = attrs.get("iso_text", getattr(self.instance, "iso_text", None))

        if listing_type == Listing.LISTING_TYPE_BUY:
            if price is None:
                raise serializers.ValidationError({"price": "Price is required for buy listings."})
            if price < 0:
                raise serializers.ValidationError({"price": "Price cannot be negative."})
            attrs["iso_text"] = None

        if listing_type == Listing.LISTING_TYPE_SWAP:
            if not iso_text:
                raise serializers.ValidationError({"iso_text": "ISO text is required for swap listings."})
            attrs["price"] = None

        return attrs
