from django.urls import path
from adoption.api.views.me import MeView
from adoption.api.views.profile import ProfileView
from adoption.api.views.pets_feed import PetsFeedView
from adoption.api.views.pets_detail import PetDetailView
from adoption.api.views.interests_create import PetInterestCreateView
from adoption.api.views.interests_list import InterestsListView
from adoption.api.views.applications_list import ApplicationsListView

from adoption.api.views.pet_apply import PetApplyCreateView



urlpatterns = [
    path("me", MeView.as_view(), name="v1-me"),
    path("profile", ProfileView.as_view(), name="v1-profile"),
    path("pets", PetsFeedView.as_view(), name="v1-pets-feed"),
    path("pets/<uuid:pet_id>", PetDetailView.as_view(), name="v1-pets-detail"),
    path("pets/<uuid:pet_id>/interest", PetInterestCreateView.as_view(), name="v1-pets-interest-create"),
    path("interests", InterestsListView.as_view(), name="v1-interests-list"),
    path("pets/<uuid:pet_id>/apply", PetApplyCreateView.as_view(), name="v1-pets-apply"),
    path("applications", ApplicationsListView.as_view()),

]

