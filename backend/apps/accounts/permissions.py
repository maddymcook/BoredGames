from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSelfOrAdminReadOnlyElseCreate(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("POST",):
            return True
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return obj.id == request.user.id or request.user.is_staff
