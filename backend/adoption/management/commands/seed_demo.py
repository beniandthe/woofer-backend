from django.core.management.base import BaseCommand
from django.utils import timezone
from adoption.models import Organization, Pet

class Command(BaseCommand):
    help = "Seed demo organization + pets for local testing"

    def handle(self, *args, **options):
        org, _ = Organization.objects.get_or_create(
            source="DEMO",
            source_org_id="demo-org-1",
            defaults={
                "name": "Demo Rescue",
                "contact_email": "demo@example.com",
                "location": "Los Angeles, CA",
                "is_active": True,
            },
        )

        created = 0
        for i in range(12):
            pet, was_created = Pet.objects.get_or_create(
                source="DEMO",
                external_id=f"demo-pet-{i}",
                defaults={
                    "organization": org,
                    "name": f"Demo Pet {i}",
                    "species": Pet.Species.DOG,
                    "status": Pet.Status.ACTIVE,
                    "listed_at": timezone.now(),
                    "photos": [],
                    "raw_description": "Demo description",
                    "ai_description": "Friendly demo pet.",
                    "temperament_tags": ["FRIENDLY"],
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Seed complete. Created {created} pets."))
