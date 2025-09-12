from django.contrib import admin
from . models import Booking, Listing, Review, Payment

# Register your models here.
admin.site.register(Booking, Listing, Review, Payment)
