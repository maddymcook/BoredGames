"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .forms import AppLoginForm
from .views import (
    HealthCheckView,
    browse_listings_view,
    create_listing_view,
    edit_profile_view,
    home,
    inbox_view,
    message_seller_view,
    my_profile_view,
    signup_view,
)

urlpatterns = [
    path("", home, name="home"),
    path("signup/", signup_view, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="auth/login.html",
            authentication_form=AppLoginForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("profile/edit/", edit_profile_view, name="edit_profile"),
    path("profile/me/", my_profile_view, name="my_profile"),
    path("browse/", browse_listings_view, name="browse_listings"),
    path("listings/new/", create_listing_view, name="create_listing"),
    path("listings/<int:listing_id>/message/", message_seller_view, name="message_seller"),
    path("inbox/", inbox_view, name="inbox"),
    path('admin/', admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.listings.urls")),
    path("api/", include("apps.messaging.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
