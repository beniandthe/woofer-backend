from django.core.management.base import BaseCommand
from adoption.models import Pet
from django.db.models import Q
from adoption.services.pet_enrichment_service import PetEnrichmentService

class Command(BaseCommand):
    help = "Backfill ai_description for ACTIVE pets that have raw_description but no ai_description."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        limit = int(opts["limit"])
        dry_run = bool(opts["dry_run"])

        qs = (
            Pet.objects
            .filter(status=Pet.Status.ACTIVE)
            .filter(Q(ai_description__isnull=True) | Q(ai_description=""))
            .exclude(raw_description__isnull=True)
            .exclude(raw_description__exact="")
            # deterministic order - pick one and keep it stable
            .order_by("-listed_at", "-pet_id")[:limit]
        )

        updated = 0
        for pet in qs:
            gen = PetEnrichmentService.generate_fun_neutral_summary(pet.raw_description)
            if not gen:
                continue

            updated += 1
            if not dry_run:
                pet.ai_description = gen
                pet.save(update_fields=["ai_description"])

        self.stdout.write(
            self.style.SUCCESS(f"Enrichment backfill complete: updated={updated} dry_run={dry_run}")
        )
