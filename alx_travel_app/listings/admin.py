from django.contrib import admin
from .models import Booking, Listing, Review, Payment

admin.site.register(Booking)
admin.site.register(Listing)
admin.site.register(Review)
admin.site.register(Payment)
