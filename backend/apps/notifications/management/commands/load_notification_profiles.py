from django.core.management.base import BaseCommand

from apps.notifications.models import NotificationRoleProfile


class Command(BaseCommand):
    help = "Crea i profili di notifica default per ogni ruolo GRC"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reimposta tutti i profili ai valori default",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            NotificationRoleProfile.objects.all().delete()
            self.stdout.write(self.style.WARNING("Profili eliminati."))

        created = NotificationRoleProfile.get_or_create_defaults()
        total = NotificationRoleProfile.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Completato: {created} profili creati, "
            f"{total - created} già esistenti. Totale: {total}"
        ))
