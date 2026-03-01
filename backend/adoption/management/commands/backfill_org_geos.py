from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from adoption.models import Organization
from adoption.services.zip_geo_service import ZipGeoService


@dataclass
class BackfillStats:
    scanned: int = 0
    eligible: int = 0
    updated: int = 0
    skipped_no_postal: int = 0
    skipped_no_match: int = 0


class Command(BaseCommand):
    help = "Backfill Organization.latitude/longitude from Organization.postal_code using offline ZIP centroid lookup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute changes and print summary, but do not write to DB.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=1000,
            help="Max number of eligible orgs to process.",
        )

    def handle(self, *args, **opts):
        dry_run: bool = bool(opts["dry_run"])
        limit: int = int(opts["limit"])

        stats = BackfillStats()
        now = timezone.now()

        qs = (
            Organization.objects
            .filter(postal_code__isnull=False)
            .exclude(postal_code__exact="")
            .filter(latitude__isnull=True)  # v0: only fill missing coords
            .order_by("organization_id")[:limit]
        )

        stats.eligible = qs.count()

        self.stdout.write(self.style.NOTICE("BackfillOrgGeos starting..."))
        self.stdout.write(f"  dry_run={dry_run} limit={limit} eligible={stats.eligible}")

        # We do per-row saves. This is deterministic and safe for MVP size.
        # If you later want speed: bulk_update in batches.
        for org in qs:
            stats.scanned += 1

            z = ZipGeoService.normalize_zip(org.postal_code)
            if not z:
                stats.skipped_no_postal += 1
                continue

            res = ZipGeoService.lookup(z)
            if not res:
                stats.skipped_no_match += 1
                continue

            # Set fields
            org.latitude = res.lat
            org.longitude = res.lon
            org.geo_source = "ZIP"
            org.geo_updated_at = now

            if not dry_run:
                org.save(update_fields=["latitude", "longitude", "geo_source", "geo_updated_at"])

            stats.updated += 1

        self.stdout.write(self.style.SUCCESS("BackfillOrgGeos complete."))
        self.stdout.write(
            "\n".join([
                "Backfill result:",
                f"  scanned={stats.scanned}",
                f"  eligible={stats.eligible}",
                f"  updated={stats.updated}",
                f"  skipped_no_postal={stats.skipped_no_postal}",
                f"  skipped_no_match={stats.skipped_no_match}",
                f"  dry_run={dry_run}",
            ])
        )