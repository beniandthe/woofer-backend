from __future__ import annotations

from django.conf import settings

from providers.base import ProviderClient, ProviderName
from providers.rescuegroups.client import RescueGroupsClient


def get_provider_client(provider: ProviderName) -> ProviderClient:
    """
    Canon boundary: central factory for provider adapters.
    Add new providers here without touching ingestion or commands.
    """
    if provider == "rescuegroups":
        if not settings.RESCUEGROUPS_API_KEY:
            raise ValueError("Missing RESCUEGROUPS_API_KEY")
        return RescueGroupsClient(
            api_key=settings.RESCUEGROUPS_API_KEY,
            base_url=getattr(settings, "RESCUEGROUPS_API_BASE_URL", "https://api.rescuegroups.org/v5"),
        )

    raise ValueError(f"Unknown provider: {provider}")
