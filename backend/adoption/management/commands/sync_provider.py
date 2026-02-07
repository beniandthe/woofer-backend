from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
import sys
import time

class Command(BaseCommand):
    help = "Scheduler-safe wrapper for provider ingestion (returns exit codes)."

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
            help="Max number of pets to ingest.",
        )
        parser.add_argument(
            "--mode",
            type=str,
            choices=["full", "incremental"],
            default="incremental",
            help="Ingestion mode (recorded only; behavior same as full for now).",
        )
        parser.add_argument(
            "--org-id",
            type=str,
            default=None,
            help="Optional external org id to scope ingestion.",
        )

    def handle(self, *args, **options):
        t0 = time.time()

        provider = options["provider"]
        limit = options["limit"]
        mode = options["mode"]
        org_id = options["org_id"]

        try:
            call_command(
                "ingest_provider",
                "--provider", provider,
                "--limit", str(limit),
                "--mode", mode,
                *(["--org-id", org_id] if org_id else []),
            )
        except Exception as e:
            elapsed = time.time() - t0
            self.stderr.write(
                f"[SYNC FAILED] provider={provider} elapsed={elapsed:.2f}s error={e}"
            )
            sys.exit(1)

        elapsed = time.time() - t0
        self.stdout.write(
            f"[SYNC OK] provider={provider} elapsed={elapsed:.2f}s"
        )
        sys.exit(0)

