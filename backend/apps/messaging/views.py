from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets

from .models import Message
from .permissions import IsMessagePartyOrAdmin
from .serializers import MessageSerializer


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsMessagePartyOrAdmin]
    queryset = Message.objects.select_related("sender", "recipient", "listing").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset

        scoped_queryset = queryset.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        )

        mark_read = self.request.query_params.get("mark_read", "false").lower() == "true"
        if mark_read:
            scoped_queryset.filter(recipient=self.request.user, is_read=False).update(is_read=True)

        return scoped_queryset

    def perform_create(self, serializer):
        sender = serializer.validated_data.get("sender")
        if not self.request.user.is_staff and sender != self.request.user:
            raise PermissionDenied("You can only send messages as yourself.")
        serializer.save()
