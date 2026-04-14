from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.accounts.models import GenreTag, Profile
from apps.listings.models import Listing
from apps.messaging.models import Message

UserAccount = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = UserAccount
        fields = ("email", "username", "password1", "password2")


class ProfileForm(forms.ModelForm):
    genres = forms.ModelMultipleChoiceField(
        queryset=GenreTag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Profile
        fields = ("display_name", "credentials", "looking_for", "genres")


class ListingForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=GenreTag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Listing
        fields = ("title", "description", "listing_type", "price", "iso_text", "tags")


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("content",)


class AppLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email")
