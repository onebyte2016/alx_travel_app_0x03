import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

# from alx_travel_app.alx_travel_app import settings

User = get_user_model()

class Listing(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    location = models.CharField(max_length=255)
    image = models.ImageField(upload_to='listing_images/', blank=True, null=True)  # new field
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# class Booking(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
#     listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bookings")
#     check_in = models.DateField()
#     check_out = models.DateField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.user.username} booked {self.listing.title}"

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings", null=True, blank=True)
    guest_name = models.CharField(max_length=255, blank=True, null=True)
    guest_email = models.EmailField(blank=True, null=True)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bookings")
    check_in = models.DateField()
    check_out = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} booked {self.listing.title}"

# class Booking(models.Model):
#     user_id = models.ForeignKey(User, on_delete=models.CASCADE)
#     listing_id = models.ForeignKey(Listing, on_delete=models.CASCADE)
#     check_in = models.DateField()
#     check_out = models.DateField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.user.username} booked {self.listing.title}"


class Review(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    listing_id = models.ForeignKey(Listing, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.listing.title}"

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")

    # Monetary
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="ETB")  # or "USD" per your usage

    # Chapa fields
    tx_ref = models.CharField(max_length=100, unique=True)      # your internal tx reference sent to Chapa
    chapa_txn_id = models.CharField(max_length=100, blank=True) # returned by Chapa (if any)
    checkout_url = models.URLField(blank=True)                  # redirect URL from initialize

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    raw_init_response = models.JSONField(blank=True, null=True)
    raw_verify_response = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Payment {self.tx_ref} / {self.status}"