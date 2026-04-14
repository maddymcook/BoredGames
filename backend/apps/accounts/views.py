from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .permissions import IsSelfOrAdminReadOnlyElseCreate
from .serializers import UserSerializer

UserAccount = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = UserAccount.objects.all().order_by("id")
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsSelfOrAdminReadOnlyElseCreate()]
