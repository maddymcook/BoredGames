from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "recipient", "listing", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "sender__email", "recipient__email")
