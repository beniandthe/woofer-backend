from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("pets/<uuid:pet_id>/like/", views.like_pet, name="like_pet"),
    path("pets/<uuid:pet_id>/apply/", views.apply_pet, name="pet_apply"),
    path("profile/", views.profile, name="profile"),
    path("applications/", views.applications, name="applications"),

]
