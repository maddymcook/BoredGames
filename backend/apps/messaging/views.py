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

        user_id = self.request.query_params.get("user")
        if user_id:
            return queryset.filter(Q(sender_id=user_id) | Q(recipient_id=user_id))

        return queryset.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        )

    def perform_create(self, serializer):
        sender = serializer.validated_data.get("sender")
        if not self.request.user.is_staff and sender != self.request.user:
            raise PermissionDenied("You can only send messages as yourself.")
        serializer.save()
