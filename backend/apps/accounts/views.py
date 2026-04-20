from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Profile
from .permissions import IsSelfOrAdminReadOnlyElseCreate
from .serializers import ProfileSerializer, UserSerializer

UserAccount = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = UserAccount.objects.select_related("profile").all().order_by("id")
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsSelfOrAdminReadOnlyElseCreate()]


class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={"display_name": request.user.username or request.user.email},
        )
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={"display_name": request.user.username or request.user.email},
        )
        serializer = ProfileSerializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
