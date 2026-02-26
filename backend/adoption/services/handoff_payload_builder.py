from __future__ import annotations
from typing import Dict, Any

from adoption.models import Pet, Organization, AdopterProfile


class HandoffPayloadBuilder:
    """
    v1 canonical handoff payload.
    Must be deterministic + safe to store.
    """

    @staticmethod
    def build(*, pet: Pet, organization: Organization, profile: AdopterProfile, user) -> Dict[str, Any]:
        # Preferences are freeform JSON, keep as is
        prefs = profile.preferences or {}

        return {
            "version": "v1",
            "type": "APPLICATION_HANDOFF",
            "pet": {
                "pet_id": str(pet.pet_id),
                "name": pet.name,
                "species": pet.species,
                "age_group": pet.age_group,
                "size": pet.size,
                "apply_url": getattr(pet, "apply_url", "") or "",
                "apply_hint": getattr(pet, "apply_hint", "") or "",
            },
            "organization": {
                "organization_id": str(organization.organization_id),
                "name": organization.name,
                "contact_email": organization.contact_email,
                "location": organization.location,
                "postal_code": getattr(organization, "postal_code", "") or "",
            },
            "adopter": {
                "user_id": str(user.id),
                "username": getattr(user, "username", None),
                "email": getattr(user, "email", None),
                "profile_snapshot": {
                    "home_type": profile.home_type,
                    "has_kids": profile.has_kids,
                    "has_dogs": profile.has_dogs,
                    "has_cats": profile.has_cats,
                    "activity_level": profile.activity_level,
                    "experience_level": profile.experience_level,
                    # keep preferences stable & explicit
                    "preferences": prefs,
                    # if present in serializer/model
                    "home_postal_code": getattr(profile, "home_postal_code", "") or "",
                },
            },
            "disclaimer": {
                "application_is_not_approval": True,
                "organization_will_contact_adopter": True,
            },
        }