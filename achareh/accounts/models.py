from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import random
from datetime import timedelta
from django.utils import timezone
from .validators import validate_iranian_mobile


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None):
        if not phone_number:
            raise ValueError('Users must have a phone number')
        user = self.model(phone_number=phone_number)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None):
        user = self.create_user(phone_number, password=password)
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, phone_number):
        return self.get(phone_number=phone_number)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=11, unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone_number


def get_expiration_time():
    return timezone.now() + timedelta(minutes=5)


class VerificationCode(models.Model):
    phone_number = models.CharField(max_length=15, unique=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=get_expiration_time)

    def generate_code(self):
        self.code = str(random.randint(100000, 999999))
        self.expires_at = get_expiration_time()
        self.save()

    def is_valid(self):
        return timezone.now() < self.expires_at

    def __str__(self):
        return f'{self.phone_number} - {self.code}'


class FailedAttempt(models.Model):
    ip_address = models.GenericIPAddressField()
    phone_number = models.CharField(max_length=11, validators=[validate_iranian_mobile], null=True, blank=True)
    attempt_type = models.CharField(max_length=20)  # 'login' or 'verification'
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ip_address} - {self.phone_number} - {self.attempt_type} - {self.timestamp}"
