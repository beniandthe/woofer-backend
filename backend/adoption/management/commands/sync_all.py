from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Convenience command: ingest provider data then enrich missing ai_description."

    def add_arguments(self, parser):
        parser.add_argument("--provider", type=str, default="rescuegroups")
        parser.add_argument("--limit", type=int, default=200)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        provider = opts["provider"]
        limit = opts["limit"]
        dry_run = opts["dry_run"]

        self.stdout.write(self.style.NOTICE("SyncAll starting..."))

        ingest_args = ["--provider", provider, "--limit", str(limit)]
        if dry_run:
            ingest_args.append("--dry-run")

        call_command("ingest_provider", *ingest_args)

        enrich_args = ["--limit", str(limit)]
        if dry_run:
            enrich_args.append("--dry-run")

        call_command("enrich_pets", *enrich_args)

        self.stdout.write(self.style.SUCCESS("SyncAll complete."))