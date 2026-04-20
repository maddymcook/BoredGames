from rest_framework import serializers

from apps.accounts.models import GenreTag
from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=80),
        required=False,
        write_only=True,
    )
    tags = serializers.SerializerMethodField(read_only=True)
    owner_display_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Listing
        fields = (
            "id",
            "owner",
            "owner_display_name",
            "title",
            "description",
            "image",
            "listing_type",
            "price",
            "iso_text",
            "tags",
            "tag_names",
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

    def get_tags(self, obj):
        return [tag.name for tag in obj.tags.all().order_by("name")]

    def get_owner_display_name(self, obj):
        profile = getattr(obj.owner, "profile", None)
        if profile and profile.display_name:
            return profile.display_name
        return obj.owner.username or obj.owner.email

    def _set_tags_from_names(self, listing, tag_names):
        cleaned = [name.strip().lower() for name in tag_names if name and name.strip()]
        if not cleaned:
            return
        tags = [GenreTag.objects.get_or_create(name=name)[0] for name in cleaned]
        listing.tags.set(tags)

    def create(self, validated_data):
        tag_names = validated_data.pop("tag_names", [])
        listing = super().create(validated_data)
        self._set_tags_from_names(listing, tag_names)
        return listing

    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        listing = super().update(instance, validated_data)
        if tag_names is not None:
            self._set_tags_from_names(listing, tag_names)
        return listing
