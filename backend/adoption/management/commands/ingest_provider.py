from __future__ import annotations

from typing import List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from providers.base import ProviderName
from providers.factory import get_provider_client

from adoption.services.provider_mappers.base import canonical_org_dict, canonical_pet_dict
from adoption.services.ingestion_service import IngestionService
from adoption.services.risk_backfill_service import RiskBackfillService


class DryRunRollback(Exception):
    """Used to force rollback in dry-run mode while still exercising write code paths."""


class Command(BaseCommand):
    help = "Ingest pets + organizations from a provider adapter into canonical models (manual trigger)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--provider",
            type=str,
            required=True,
            help="Provider name (e.g. rescuegroups).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Max number of pets to ingest (approx).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch + map + run ingestion inside a transaction, then roll back (no DB writes).",
        )
        parser.add_argument(
            "--org-id",
            type=str,
            default=None,
            help="Optional external org id to scope ingestion.",
        )

    def handle(self, *args, **options):
        provider_raw = options["provider"].strip().lower()
        limit: int = options["limit"]
        dry_run: bool = options["dry_run"]
        org_id: Optional[str] = options["org_id"]

        try:
            provider: ProviderName = provider_raw  # type: ignore
        except Exception:
            raise CommandError(f"Invalid provider value: {provider_raw}")

        try:
            client = get_provider_client(provider)
        except Exception as e:
            raise CommandError(str(e))

        self.stdout.write(self.style.NOTICE("Ingest starting..."))
        self.stdout.write(f"  provider={provider} limit={limit} org_id={org_id or 'ALL'} dry_run={dry_run}")

        # 1) Fetch provider-normalized records
        org_records = list(client.iter_orgs(limit=500 if org_id is None else 10, org_id=org_id))
        pet_records = list(client.iter_pets(limit=limit, org_id=org_id))

        self.stdout.write(self.style.NOTICE(f"Fetched provider records: orgs={len(org_records)} pets={len(pet_records)}"))

        # 2) Map to canonical dicts
        org_dicts = [canonical_org_dict(o) for o in org_records]
        pet_dicts = [canonical_pet_dict(p) for p in pet_records]

        # 3) Ingest + risk backfill (dry-run uses rollback)
        if dry_run:
            try:
                with transaction.atomic():
                    result = IngestionService.ingest_canonical(org_dicts, pet_dicts)
                    # Backfill only over ingested pets would be ideal, but canon allows safe all-active backfill.
                    risk_count = 0
                    self.stdout.write(self._format_result(result, risk_count, dry_run=True))
                    raise DryRunRollback()
            except DryRunRollback:
                self.stdout.write(self.style.WARNING("Dry-run complete (rolled back)."))
            return

        result = IngestionService.ingest_canonical(org_dicts, pet_dicts)
        risk_count = RiskBackfillService.backfill_all_active()

        self.stdout.write(self._format_result(result, risk_count, dry_run=False))
        self.stdout.write(self.style.SUCCESS("Ingest complete."))

    def _format_result(self, result, risk_count: int, dry_run: bool) -> str:
        return (
            "Ingestion result:\n"
            f"  organizations_created={result.organizations_created}\n"
            f"  organizations_updated={result.organizations_updated}\n"
            f"  pets_created={result.pets_created}\n"
            f"  pets_updated={result.pets_updated}\n"
            f"  pets_skipped={result.pets_skipped}\n"
            f"  risk_backfilled={risk_count}\n"
            f"  mode={'DRY_RUN' if dry_run else 'WRITE'}\n"
        )

