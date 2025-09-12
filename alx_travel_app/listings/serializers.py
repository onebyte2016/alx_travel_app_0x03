from rest_framework import serializers
from .models import Listing, Booking

class ListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = '__all__'


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ["id", "user", "guest_name", "guest_email", "listing", "check_in", "check_out", "created_at"]
        read_only_fields = ["id", "created_at", "user"]  # user is auto-set if logged in
