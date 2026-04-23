from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Listing, ListingRating
from .permissions import IsOwnerOrAdminOrReadOnly
from .serializers import ListingSerializer


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.select_related(
        "owner",
        "owner__profile",
        "approved_by",
        "approved_by__profile",
    ).prefetch_related(
        "tags",
        "ratings",
        "ratings__user",
        "ratings__user__profile",
    ).all().order_by("-created_at")
    serializer_class = ListingSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["listing_type", "owner", "approval_status"]
    search_fields = ["title", "description", "iso_text", "tags__name"]
    ordering_fields = ["created_at", "updated_at", "price"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action in ("rate",):
            return [IsAuthenticated()]
        return [IsOwnerOrAdminOrReadOnly()]

    def get_queryset(self):
        queryset = super().get_queryset()
        listing_type = self.request.query_params.get("type")
        if listing_type:
            queryset = queryset.filter(listing_type=listing_type)

        user = self.request.user
        if not user.is_authenticated or not user.is_staff:
            queryset = queryset.filter(approval_status=Listing.STATUS_APPROVED)

        return queryset

    def perform_create(self, serializer):
        owner = serializer.validated_data.get("owner")
        if not self.request.user.is_staff and owner != self.request.user:
            raise PermissionDenied("You can only create listings for yourself.")

        approval_status = Listing.STATUS_APPROVED if self.request.user.is_staff else Listing.STATUS_PENDING
        serializer.save(approval_status=approval_status)

    @action(detail=True, methods=["post"])
    def rate(self, request, pk=None):
        listing = self.get_object()

        score = request.data.get("score")
        review = request.data.get("review", "")

        if score is None:
            return Response(
                {"score": "Score is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            score = int(score)
        except (TypeError, ValueError):
            return Response(
                {"score": "Score must be an integer between 1 and 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rating, created = ListingRating.objects.update_or_create(
            listing=listing,
            user=request.user,
            defaults={"score": score, "review": review},
        )

        return Response(
            {
                "message": "Rating submitted." if created else "Rating updated.",
                "average_rating": listing.average_rating,
                "rating_count": listing.rating_count,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not request.user.is_staff:
            return Response(
                {"detail": "Not authorized."},
                status=status.HTTP_403_FORBIDDEN,
            )

        listing = Listing.objects.get(pk=pk)
        listing.approval_status = Listing.STATUS_APPROVED
        listing.approved_by = request.user
        listing.approved_at = timezone.now()
        listing.save()

        return Response({"message": "Listing approved."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not request.user.is_staff:
            return Response(
                {"detail": "Not authorized."},
                status=status.HTTP_403_FORBIDDEN,
            )

        listing = Listing.objects.get(pk=pk)
        listing.approval_status = Listing.STATUS_REJECTED
        listing.approved_by = None
        listing.approved_at = None
        listing.save()

        return Response({"message": "Listing rejected."}, status=status.HTTP_200_OK)