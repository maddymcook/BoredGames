from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect

from apps.accounts.models import GenreTag, Profile
from apps.listings.models import Listing
from apps.messaging.models import Message
from .forms import AppLoginForm, ListingForm, MessageForm, ProfileForm, SignUpForm
from rest_framework.response import Response
from rest_framework.views import APIView


def home(request):
    ensure_default_genres()
    listings = Listing.objects.select_related("owner").prefetch_related("tags").all()[:6]
    return render(request, "home.html", {"listings": listings})


def ensure_default_genres():
    for name in [
        "Fantasy",
        "Deck Building",
        "Card Game",
        "Co-op",
        "Strategy",
        "Family",
        "Party",
    ]:
        GenreTag.objects.get_or_create(name=name)


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(
                user=user,
                defaults={"display_name": user.username},
            )
            login(request, user)
            return redirect("edit_profile")
    else:
        form = SignUpForm()
    return render(request, "auth/signup.html", {"form": form})


@login_required
def edit_profile_view(request):
    ensure_default_genres()
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"display_name": request.user.username},
    )
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("my_profile")
    else:
        form = ProfileForm(instance=profile)
    return render(request, "profiles/edit.html", {"form": form})


@login_required
def my_profile_view(request):
    profile = get_object_or_404(Profile.objects.prefetch_related("genres"), user=request.user)
    listings = Listing.objects.filter(owner=request.user).prefetch_related("tags")
    return render(
        request,
        "profiles/detail.html",
        {"profile": profile, "listings": listings},
    )


def browse_listings_view(request):
    queryset = Listing.objects.select_related("owner").prefetch_related("tags").all()
    q = request.GET.get("q")
    listing_type = request.GET.get("type")
    tag = request.GET.get("tag")

    if q:
        queryset = queryset.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(iso_text__icontains=q))
    if listing_type in {Listing.LISTING_TYPE_SWAP, Listing.LISTING_TYPE_BUY}:
        queryset = queryset.filter(listing_type=listing_type)
    if tag:
        queryset = queryset.filter(tags__name__iexact=tag)

    return render(request, "listings/browse.html", {"listings": queryset.distinct()})


@login_required
def create_listing_view(request):
    ensure_default_genres()
    if request.method == "POST":
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.save()
            form.save_m2m()
            messages.success(request, "Listing created.")
            return redirect("browse_listings")
    else:
        form = ListingForm()
    return render(request, "listings/create.html", {"form": form})


@login_required
def message_seller_view(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    if listing.owner_id == request.user.id:
        messages.error(request, "You cannot message yourself about your own listing.")
        return redirect("browse_listings")

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.recipient = listing.owner
            msg.listing = listing
            msg.save()
            messages.success(request, "Message sent to seller.")
            return redirect("inbox")
    else:
        form = MessageForm()

    return render(request, "messages/send.html", {"form": form, "listing": listing})


@login_required
def inbox_view(request):
    messages_qs = Message.objects.select_related("sender", "listing").filter(recipient=request.user)
    return render(request, "messages/inbox.html", {"inbox_messages": messages_qs})


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})
