from adoption.models import AdopterProfile

class UserProfileService:
    ALLOWED_FIELDS = {
        "home_type",
        "has_kids",
        "has_dogs",
        "has_cats",
        "activity_level",
        "experience_level",
        "preferences",
    }

    @staticmethod
    def get_or_create_profile(user) -> AdopterProfile:
        profile, _ = AdopterProfile.objects.get_or_create(user=user)
        return profile

    @staticmethod
    def update_profile(user, payload: dict) -> AdopterProfile:
        profile = UserProfileService.get_or_create_profile(user)

        for k, v in (payload or {}).items():
            if k in UserProfileService.ALLOWED_FIELDS:
                setattr(profile, k, v)

        profile.save()
        return profile
