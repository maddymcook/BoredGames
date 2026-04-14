from django.contrib import admin
from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "listing_type", "owner", "price", "created_at")
    list_filter = ("listing_type", "created_at")
    search_fields = ("title", "description", "iso_text", "owner__email")
    filter_horizontal = ("tags",)
