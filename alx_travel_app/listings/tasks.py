# listings/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Payment


@shared_task
def send_payment_confirmation_email(payment_id: str):
    try:
        payment = Payment.objects.select_related("booking", "user").get(id=payment_id)
    except Payment.DoesNotExist:
        return

    subject = "Payment Confirmation - ALX Travel"
    message = (
        f"Hello {payment.user.get_full_name() or payment.user.email},\n\n"
        f"Your payment for booking {payment.booking.reference} was successful.\n"
        f"Amount: {payment.amount} {payment.currency}\n"
        f"Transaction Ref: {payment.tx_ref}\n\n"
        "Thank you for booking with us!"
    )
    recipient = [payment.user.email] if payment.user.email else []
    if recipient:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient, fail_silently=True)


@shared_task
def send_booking_confirmation_email(customer_email, booking_id, trip_name):
    subject = "Booking Confirmation"
    message = f"Dear Customer,\n\nYour booking (ID: {booking_id}) for {trip_name} has been confirmed.\n\nThank you for choosing us!"
    send_mail(
        subject,
        message,
        'ogboemmandu@gmail.com',  # from email
        [customer_email],
        fail_silently=False,
    )
    return f"Confirmation email sent to {customer_email} for booking {booking_id}"