from celery import shared_task
from django.utils import timezone
from .models import FailedAttempt


@shared_task
def delete_old_failed_attempts():
    # Define the threshold for old records (5 days ago)
    threshold = timezone.now() - timezone.timedelta(days=5)

    # Delete old FailedAttempt records
    deleted_count, _ = FailedAttempt.objects.filter(timestamp__lt=threshold).delete()
    return f"{deleted_count} old failed attempts deleted."
