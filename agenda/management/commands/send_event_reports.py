from django.core.management.base import BaseCommand
from agenda.services import send_event_reports

class Command(BaseCommand):
    help = "Send event reports to managers"

    def handle(self, *args, **options):
        send_event_reports()
        self.stdout.write(self.style.SUCCESS("Reports sent"))
