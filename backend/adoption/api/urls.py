from django.urls import path
from adoption.api.views.me import MeView
from adoption.api.views.profile import ProfileView


urlpatterns = [
    path("me", MeView.as_view(), name="v1-me"),
    path("profile", ProfileView.as_view(), name="v1-profile"),
]

