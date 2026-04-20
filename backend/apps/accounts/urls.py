from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MyProfileView, UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")

urlpatterns = router.urls
urlpatterns += [
    path("profiles/me/", MyProfileView.as_view(), name="my_profile_api"),
]
