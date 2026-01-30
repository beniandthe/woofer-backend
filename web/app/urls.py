from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("pets/<uuid:pet_id>/like/", views.like_pet, name="like_pet"),
    path("pets/<uuid:pet_id>/apply/<uuid:org_id>/", views.apply_pet, name="apply_pet",),

]
