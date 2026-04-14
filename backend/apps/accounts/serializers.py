from django.contrib.auth import get_user_model
from rest_framework import serializers


UserAccount = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccount
        fields = ("id", "email", "username", "is_admin", "is_staff", "is_superuser", "password")
        extra_kwargs = {
            "password": {"write_only": True, "min_length": 8},
            "is_admin": {"read_only": True},
            "is_staff": {"read_only": True},
            "is_superuser": {"read_only": True},
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = UserAccount.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
