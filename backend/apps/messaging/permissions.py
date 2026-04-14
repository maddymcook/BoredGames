from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsMessagePartyOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.sender_id == request.user.id or obj.recipient_id == request.user.id
