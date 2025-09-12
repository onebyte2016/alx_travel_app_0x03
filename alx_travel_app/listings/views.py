from django.shortcuts import render
from rest_framework import viewsets
from .models import Listing, Booking
from .serializers import ListingSerializer, BookingSerializer
import os
import uuid
import requests
from django.utils import timezone
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Booking, Payment
from .tasks import send_booking_confirmation_email



class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.user.is_authenticated:
            booking = serializer.save(user=request.user)
            email = booking.user.email
        else:
            # 👇 Ensure guest must provide name + email
            guest_name = serializer.validated_data.get("guest_name")
            guest_email = serializer.validated_data.get("guest_email")
            if not guest_name or not guest_email:
                return Response(
                    {"error": "Guests must provide name and email."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            booking = serializer.save()
            email = guest_email

        # Trigger async email
        send_booking_confirmation_email.delay(
            email,
            booking.id,
            booking.listing.title
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)




CHAPA_SECRET_KEY = os.environ.get("CHAPA_SECRET_KEY", "")
CHAPA_BASE_URL = "https://api.chapa.co/v1"  # sandbox and live share same domain; key controls env

def build_tx_ref(prefix="TRX"):
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"

def chapa_headers():
    return {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

class BookingPaymentInitView(APIView):
    """
    POST /api/bookings/{booking_id}/pay/
    Body (optional): {"return_url": "...", "callback_url": "..."}
    Returns: checkout_url from Chapa to redirect user to pay
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, booking_id):
        if not CHAPA_SECRET_KEY:
            return Response({"detail": "CHAPA_SECRET_KEY not configured"}, status=500)

        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        # Create or reuse a pending Payment for this booking
        payment = getattr(booking, "payment", None)
        if payment and payment.status == Payment.Status.COMPLETED:
            return Response({"detail": "Booking already paid.", "payment_status": payment.status}, status=400)

        if not payment:
            tx_ref = build_tx_ref(prefix="BOOKPAY")
            payment = Payment.objects.create(
                booking=booking,
                user=request.user,
                amount=booking.total_price,
                currency="ETB",   # set to the currency you actually use
                tx_ref=tx_ref,
                status=Payment.Status.PENDING,
            )
        else:
            # reuse existing tx_ref if pending/failed/canceled
            tx_ref = payment.tx_ref

        # Construct initialize payload
        # NOTE: tailor fields to your UX (names, email etc.)
        payload = {
            "amount": str(payment.amount),
            "currency": payment.currency,
            "email": request.user.email if getattr(request.user, "email", "") else "guest@example.com",
            "first_name": getattr(request.user, "first_name", "") or "Guest",
            "last_name": getattr(request.user, "last_name", "") or "User",
            "tx_ref": tx_ref,
            # After payment Chapa can redirect user to this URL
            "return_url": request.data.get("return_url", "https://your-frontend.example/booking/thank-you"),
            # Server-to-server callback (webhook-like). Optional if you only verify manually.
            "callback_url": request.data.get("callback_url", "https://your-backend.example/api/payments/chapa/callback/"),
            "customization": {
                "title": "ALX Travel Booking",
                "description": f"Payment for booking {booking.reference}",
            },
        }

        try:
            r = requests.post(f"{CHAPA_BASE_URL}/transaction/initialize", json=payload, headers=chapa_headers(), timeout=30)
            data = r.json()
        except Exception as e:
            return Response({"detail": "Chapa init failed", "error": str(e)}, status=502)

        # Expecting Chapa to return a 'status' and 'data' with 'checkout_url'
        payment.raw_init_response = data
        if r.status_code == 200 and data.get("status") == "success":
            payment.checkout_url = data.get("data", {}).get("checkout_url", "")
            payment.chapa_txn_id = data.get("data", {}).get("id", "")  # sometimes returned
            payment.save()
            return Response({
                "message": "Payment initialized",
                "booking_reference": booking.reference,
                "tx_ref": payment.tx_ref,
                "checkout_url": payment.checkout_url,
                "status": payment.status,
            }, status=200)

        # Fail soft, keep pending but surface error
        payment.save()
        return Response({
            "detail": "Failed to initialize payment with Chapa",
            "chapa_response": data
        }, status=400)


class PaymentVerifyView(APIView):
    """
    GET /api/payments/verify/?tx_ref=TRX-XXXX
    or
    POST /api/payments/verify/ {"tx_ref": "..."}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tx_ref = request.query_params.get("tx_ref")
        return self._verify(request, tx_ref)

    def post(self, request):
        tx_ref = request.data.get("tx_ref")
        return self._verify(request, tx_ref)

    def _verify(self, request, tx_ref):
        if not CHAPA_SECRET_KEY:
            return Response({"detail": "CHAPA_SECRET_KEY not configured"}, status=500)
        if not tx_ref:
            return Response({"detail": "tx_ref is required"}, status=400)

        payment = get_object_or_404(Payment, tx_ref=tx_ref, user=request.user)

        try:
            r = requests.get(f"{CHAPA_BASE_URL}/transaction/verify/{tx_ref}", headers=chapa_headers(), timeout=30)
            data = r.json()
        except Exception as e:
            return Response({"detail": "Chapa verify failed", "error": str(e)}, status=502)

        payment.raw_verify_response = data

        # Chapa returns structure like:
        # {"status":"success","data":{"tx_ref":"...","status":"success" ...}}
        chapa_status = (data.get("data") or {}).get("status", "").lower()
        if r.status_code == 200 and data.get("status") == "success" and chapa_status == "success":
            payment.status = Payment.Status.COMPLETED
            payment.verified_at = timezone.now()
            payment.save()

            # Kick off confirmation email via Celery (optional)
            try:
                from .tasks import send_payment_confirmation_email
                send_payment_confirmation_email.delay(str(payment.id))
            except Exception:
                # If Celery not configured yet, ignore
                pass

            return Response({
                "message": "Payment verified: COMPLETED",
                "tx_ref": payment.tx_ref,
                "booking_reference": payment.booking.reference,
                "status": payment.status,
                "verify_payload": data
            }, status=200)

        # Mark failed/canceled otherwise
        payment.status = Payment.Status.FAILED if chapa_status == "failed" else payment.status
        payment.save()

        return Response({
            "detail": "Payment not successful",
            "tx_ref": payment.tx_ref,
            "status": payment.status,
            "verify_payload": data
        }, status=400)
