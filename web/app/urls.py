from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("pets/<uuid:pet_id>/like/", views.like_pet, name="like_pet"),
    path("pets/<uuid:pet_id>/apply/", views.apply_pet, name="pet_apply"),
    path("profile/", views.profile, name="profile"),
    path("applications/", views.applications, name="applications"),
    path("pets/<uuid:pet_id>/pass/", views.pass_pet, name="pass_pet"),
    path("interests/", views.interests, name="interests"),
    path("pets/<uuid:pet_id>/", views.pet_detail, name="pet_detail"),
    path("foster/", views.foster, name="foster"),
    path("learn/", views.learn, name="learn"),
    path("stories/", views.stories, name="stories"),
    path("community/", views.community, name="community"),
]
