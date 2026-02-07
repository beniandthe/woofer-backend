from __future__ import annotations

from typing import List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from providers.base import ProviderName
from providers.factory import get_provider_client

from adoption.services.provider_mappers.base import canonical_org_dict, canonical_pet_dict
from adoption.services.ingestion_service import IngestionService
from adoption.services.risk_backfill_service import RiskBackfillService

from adoption.models import ProviderSyncState
from django.utils import timezone

from adoption.models import Pet
import time


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
        parser.add_argument(
            "--mode",
            type=str,
            choices=["full", "incremental"],
            default="full",
            help="Ingestion mode. Incremental is recorded but behaves like full for now.",
        )
        parser.add_argument(
            "--summary-only",
            action="store_true",
            help="Print only run summaries (default behavior).",
        )

    def handle(self, *args, **options):
        t0 = time.time()
        summary_only: bool = options["summary_only"]
        mode = options["mode"].upper()
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

        sync_state = None
        if not dry_run:
            sync_state, _ = ProviderSyncState.objects.get_or_create(provider=provider.upper())
            sync_state.last_run_started_at = timezone.now()
            sync_state.last_mode = mode
            sync_state.save(update_fields=["last_run_started_at", "last_mode"])


        self.stdout.write(self.style.NOTICE("Ingest starting..."))
        self.stdout.write(f"  provider={provider} limit={limit} org_id={org_id or 'ALL'} dry_run={dry_run}")
        # 1) Fetch provider-normalized pets first (they determine which orgs we need)
        pet_records = list(client.iter_pets(limit=limit, org_id=org_id))

        # Collect the unique org ids referenced by those pets
        needed_org_ids = sorted({p.external_org_id for p in pet_records if p.external_org_id})

        # Fetch only the orgs we actually need
        org_records = []
        for oid in needed_org_ids:
            org_records.extend(list(client.iter_orgs(limit=1, org_id=oid)))

        self.stdout.write(self.style.NOTICE(
                f"Fetched: pets={len(pet_records)} unique_org_ids={len(needed_org_ids)} orgs={len(org_records)}"
            )
        )


        # 2) Map to canonical dicts
        org_dicts = [canonical_org_dict(o) for o in org_records]
        pet_dicts = [canonical_pet_dict(p) for p in pet_records]

        # 3) Ingest + risk backfill (dry-run uses rollback)
        if dry_run:
            try:
                with transaction.atomic():
                    result = IngestionService.ingest_canonical(org_dicts, pet_dicts)
                    # Backfill only over ingested pets would be ideal, but canon allows safe all-active backfill.
                    would_deactivate = (
                        Pet.objects.filter(source=provider.upper(), status="ACTIVE")
                        .exclude(external_id__in=result.pets_seen_external_ids).count()
                    )
                    elapsed = time.time() - t0

                    risk_count = 0

                    self.stdout.write(
                        self._format_result(
                            result,
                            risk_count=0,
                            dry_run=True,
                            deactivated=would_deactivate,
                            elapsed_s=elapsed,
                        )
                    )
                    raise DryRunRollback()
                
            except DryRunRollback:
                self.stdout.write(self.style.WARNING("Dry-run complete (rolled back)."))
            return

        result = IngestionService.ingest_canonical(org_dicts, pet_dicts)
        now = timezone.now()

        # Mark seen pets' last_seen_at (provider-scoped)
        Pet.objects.filter(
            source=provider.upper(),
            external_id__in=result.pets_seen_external_ids,
        ).update(last_seen_at=now)

        # Deactivate missing pets (provider-scoped)
        deactivated = (
            Pet.objects.filter(source=provider.upper(), status="ACTIVE")
            .exclude(external_id__in=result.pets_seen_external_ids)
            .update(status="INACTIVE", last_seen_at=now)
        )

        elapsed = time.time() - t0
        risk_count = RiskBackfillService.backfill_all_active()

        self.stdout.write(
            self._format_result(
                result,
                risk_count=risk_count,
                dry_run=False,
                deactivated=deactivated,
                elapsed_s=elapsed,
            )
        )

        if sync_state is not None:
            sync_state.last_run_finished_at = timezone.now()
            sync_state.last_success_at = sync_state.last_run_finished_at
            sync_state.save(update_fields=["last_run_finished_at", "last_success_at"])

        self.stdout.write(self.style.SUCCESS("Ingest complete."))


    def _format_result(self, result, risk_count: int, dry_run: bool, deactivated: int = 0, elapsed_s: float = 0.0) -> str:
        return (
            "Ingestion result:\n"
            f"  organizations_created={result.organizations_created}\n"
            f"  organizations_updated={result.organizations_updated}\n"
            f"  pets_created={result.pets_created}\n"
            f"  pets_updated={result.pets_updated}\n"
            f"  pets_skipped={result.pets_skipped}\n"
            f"  pets_seen={len(result.pets_seen_external_ids)}\n"
            f"  pets_deactivated={deactivated}\n"
            f"  risk_backfilled={risk_count}\n"
            f"  mode={'DRY_RUN' if dry_run else 'WRITE'}\n"
            f"  elapsed_seconds={elapsed_s:.3f}\n"
        )


