from celery import shared_task
from django.core.mail import send_mail
from django.core.management import call_command


@shared_task
def send_password_reset_email(email: str, uid: str, token: str) -> None:
    # EMAIL_BACKEND is the console backend in development — the point of
    # moving this to Celery is that a slow/unreachable SMTP provider in
    # production no longer holds the request/response cycle open.
    send_mail(
        subject="Password reset",
        message=f"uid={uid}&token={token}",
        from_email=None,
        recipient_list=[email],
        fail_silently=True,
    )


@shared_task
def cleanup_expired_tokens() -> None:
    # OutstandingToken/BlacklistedToken rows (simplejwt's token_blacklist
    # app) accumulate forever otherwise — one row per refresh token ever
    # issued. flushexpiredtokens deletes only the ones already past their
    # expiry, so a live session's tokens are never touched.
    call_command("flushexpiredtokens")
