from django.core.management.base import BaseCommand
from django.utils.timezone import now
from agenda.services import send_event_reports
from datetime import datetime


class Command(BaseCommand):
    help = "Send event reports to managers"

    def handle(self, *args, **options):
        week = datetime.now().isocalendar().week

        if week % 2 != 0:
            self.stdout.write("Skipping this week")
            return

        start = now()
        self.stdout.write("Starting report sending...")
        send_event_reports()
        end = now()
        self.stdout.write(
            self.style.SUCCESS(
                f"Reports sent in {(end - start).total_seconds()} seconds"
            )
        )
        self.stdout.write(self.style.SUCCESS("Reports sent"))
