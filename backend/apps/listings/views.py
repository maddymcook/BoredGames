from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny

from .models import Listing
from .permissions import IsOwnerOrAdminOrReadOnly
from .serializers import ListingSerializer


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.select_related("owner").all().order_by("-created_at")
    serializer_class = ListingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["listing_type", "owner"]
    search_fields = ["title", "description", "iso_text"]
    ordering_fields = ["created_at", "updated_at", "price"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsOwnerOrAdminOrReadOnly()]

    def get_queryset(self):
        queryset = super().get_queryset()
        listing_type = self.request.query_params.get("type")
        if listing_type:
            queryset = queryset.filter(listing_type=listing_type)
        return queryset

    def perform_create(self, serializer):
        owner = serializer.validated_data.get("owner")
        if not self.request.user.is_staff and owner != self.request.user:
            raise PermissionDenied("You can only create listings for yourself.")
        serializer.save()
