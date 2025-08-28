from django.core.management.base import BaseCommand
from listings.models import Listing
from django.contrib.auth import get_user_model
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with sample listings'

    def handle(self, *args, **kwargs):
        locations = ['Lagos', 'Abuja', 'Kano', 'Port Harcourt', 'Ibadan']
        titles = ['Luxury Villa', 'Beach House', 'City Apartment', 'Cottage', 'Modern Flat']

        for i in range(10):
            Listing.objects.create(
                title=random.choice(titles),
                description="This is a great place to stay!",
                price_per_night=random.uniform(50, 500),
                location=random.choice(locations)
            )
        self.stdout.write(self.style.SUCCESS('✅ Successfully seeded listings.'))
