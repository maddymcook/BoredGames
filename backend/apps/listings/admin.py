from django.contrib import admin

from .models import Listing, ListingRating


class ListingRatingInline(admin.TabularInline):
    model = ListingRating
    extra = 0
    readonly_fields = ("user", "score", "review", "created_at", "updated_at")
    can_delete = False


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "owner",
        "listing_type",
        "approval_status",
        "average_rating",
        "rating_count",
        "created_at",
    )
    list_filter = ("approval_status", "listing_type", "created_at")
    search_fields = ("title", "description", "owner__email", "owner__username")
    readonly_fields = (
        "created_at",
        "updated_at",
        "approved_at",
        "average_rating",
        "rating_count",
    )
    inlines = [ListingRatingInline]
    actions = ["approve_listings", "reject_listings"]

    def approve_listings(self, request, queryset):
        queryset.update(approval_status="approved")

    approve_listings.short_description = "Approve selected listings"

    def reject_listings(self, request, queryset):
        queryset.update(approval_status="rejected", approved_by=None, approved_at=None)

    reject_listings.short_description = "Reject selected listings"


@admin.register(ListingRating)
class ListingRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "user", "score", "created_at")
    list_filter = ("score", "created_at")
    search_fields = ("listing__title", "user__email", "user__username", "review")
    readonly_fields = ("created_at", "updated_at")