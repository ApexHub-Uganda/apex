"""Seed Uganda-first academic presets for a tenant."""
from django.core.management.base import BaseCommand, CommandError

from apps.academics.services.uganda_seed import seed_uganda_presets, uganda_term_templates
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Seed Uganda assessment schemes, subject combinations, and UNEB-style grading for a school."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", type=str, required=True, help="Tenant UUID or code")
        parser.add_argument("--show-term-templates", action="store_true", help="Print suggested term dates")

    def handle(self, *args, **options):
        key = options["tenant"]
        tenant = Tenant.objects.filter(pk=key).first() or Tenant.objects.filter(code__iexact=key).first()
        if not tenant:
            raise CommandError(f"Tenant not found: {key}")
        result = seed_uganda_presets(tenant=tenant)
        self.stdout.write(self.style.SUCCESS(f"Seeded for {tenant.name}: {result}"))
        if options["show_term_templates"]:
            for t in uganda_term_templates():
                self.stdout.write(
                    f"  {t['name']}: {t['start_date']} → {t['end_date']} "
                    f"(mid-term {t['mid_term_break_start']}–{t['mid_term_break_end']})"
                )
