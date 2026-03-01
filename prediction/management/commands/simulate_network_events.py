import random
from django.core.management.base import BaseCommand
from prediction.models import NetworkEvent
from faker import Faker

class Command(BaseCommand):
    help = 'Generate simulated network events'

    def handle(self, *args, **kwargs):
        fake = Faker()
        event_types = ['Failed Login', 'Port Scan', 'DDoS Attempt', 'Malware Detected', 'Unusual Outbound Traffic']
        severities = ['low', 'medium', 'high']
        for _ in range(20):
            NetworkEvent.objects.create(
                event_type=random.choice(event_types),
                source_ip=fake.ipv4(),
                description=fake.sentence(),
                severity=random.choice(severities)
            )
        self.stdout.write(self.style.SUCCESS('Created 20 network events.'))