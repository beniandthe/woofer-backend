from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Convenience command: ingest provider data then enrich missing ai_description."

    def add_arguments(self, parser):
        parser.add_argument("--provider", type=str, default="rescuegroups")
        parser.add_argument("--limit", type=int, default=200)
        parser.add_argument("--dry-run", action="store_true")

        # Default ON behavior (use disable flag)
        parser.add_argument(
            "--no-backfill-geo",
            action="store_true",
            help="Disable automatic org geo backfill step after ingest (default is enabled).",
        )

    def handle(self, *args, **opts):
        provider = opts["provider"]
        limit = opts["limit"]
        dry_run = opts["dry_run"]
        backfill_geo = not opts["no_backfill_geo"]

        self.stdout.write(self.style.NOTICE("SyncAll starting..."))

        ingest_args = ["--provider", provider, "--limit", str(limit)]
        if dry_run:
            ingest_args.append("--dry-run")

        call_command("ingest_provider", *ingest_args)

        # keep “one command = correct distance feed”
        if backfill_geo:
            backfill_args = []
            if dry_run:
                backfill_args.append("--dry-run")
            call_command("backfill_org_geos", *backfill_args)

        enrich_args = ["--limit", str(limit)]
        if dry_run:
            enrich_args.append("--dry-run")

        call_command("enrich_pets", *enrich_args)

        self.stdout.write(self.style.SUCCESS("SyncAll complete."))