import re
from django.core.exceptions import ValidationError


def validate_iranian_mobile(value):
    pattern = r'^09[0-9]{9}$'
    if not re.match(pattern, value):
        raise ValidationError("The phone number must be a valid.")
