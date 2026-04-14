from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import GenreTag, Profile, UserAccount


@admin.register(UserAccount)
class UserAccountAdmin(UserAdmin):
    model = UserAccount
    list_display = ("id", "email", "username", "is_admin", "is_staff", "is_superuser")
    ordering = ("id",)
    fieldsets = UserAdmin.fieldsets + (
        ("BoredGames", {"fields": ("is_admin",)}),
    )


@admin.register(GenreTag)
class GenreTagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "display_name", "user", "updated_at")
    search_fields = ("display_name", "user__email", "looking_for")
    filter_horizontal = ("genres",)
