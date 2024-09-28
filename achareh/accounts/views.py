from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import CustomUser, VerificationCode, FailedAttempt
from .serializers import RegisterSerializer, LoginSerializer, VerifyCodeSerializer, UserDetailsSerializer, \
    PasswordSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta


class BlockableView:
    """
    Base class to handle IP and phone number blocking.
    """

    def is_blocked(self, ip_address, phone_number, attempt_type):
        attempts = FailedAttempt.objects.filter(
            ip_address=ip_address,
            phone_number=phone_number,
            attempt_type=attempt_type,
            timestamp__gte=timezone.now() - timedelta(hours=1)
        )
        return attempts.count() >= 3


class RegisterView(BlockableView, generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        ip_address = request.META.get('REMOTE_ADDR')

        if not phone_number:
            return Response({'detail': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if self.is_blocked(ip_address, phone_number, 'verification'):
            return Response({'detail': 'Too many failed attempts. Please try again later.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Delete expired verification codes
        VerificationCode.objects.filter(phone_number=phone_number, expires_at__lt=timezone.now()).delete()

        if VerificationCode.objects.filter(phone_number=phone_number).exists():
            return Response({'detail': 'Verification code already sent for this phone number.'},
                            status=status.HTTP_400_BAD_REQUEST)

        code = VerificationCode.objects.create(phone_number=phone_number)
        code.generate_code()

        # send_sms(phone_number, code.code)

        # For test: Receive a verify code
        print(code)

        # Returning the verification code in the response for testing purposes only.
        # This is to facilitate the testing process by allowing direct access to the code.
        return Response({'detail': 'Verification code sent.', 'verification_code': code.code},
                        status=status.HTTP_200_OK)


class VerifyCodeView(BlockableView, generics.GenericAPIView):
    serializer_class = VerifyCodeSerializer

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')
        ip_address = request.META.get('REMOTE_ADDR')

        if not phone_number or not code:
            return Response({'detail': 'Phone number and code are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if self.is_blocked(ip_address, phone_number, 'verification'):
            return Response({'detail': 'Too many failed attempts. Please try again later.'},
                            status=status.HTTP_403_FORBIDDEN)

        verification_code = VerificationCode.objects.filter(
            phone_number=phone_number,
            code=code,
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).first()

        if verification_code and verification_code.is_valid():
            user, created = CustomUser.objects.get_or_create(phone_number=phone_number)
            if created:
                user.set_unusable_password()
                user.save()

            # Generate JWT token
            refresh = RefreshToken.for_user(user)

            # Optionally delete the verification code after successful verification
            verification_code.delete()

            return Response({
                'detail': 'Verification successful. Please set your password.',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        else:
            FailedAttempt.objects.create(ip_address=ip_address, phone_number=phone_number, attempt_type='verification')
            return Response({'detail': 'Invalid code or code expired.'}, status=status.HTTP_400_BAD_REQUEST)


class SetPasswordView(generics.GenericAPIView):
    serializer_class = PasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user.set_password(serializer.validated_data.get('password'))
            user.save()
            return Response({'detail': 'Password set successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(BlockableView, generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')
        ip_address = request.META.get('REMOTE_ADDR')

        # Validate inputs
        if not phone_number or not password:
            return Response({'detail': 'Phone number and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if IP or phone number is blocked
        if self.is_blocked(ip_address, phone_number, 'login'):
            return Response({'detail': 'Too many failed attempts. Please try again later.'},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            user = CustomUser.objects.get(phone_number=phone_number)
            if user.check_password(password):
                # Generate JWT token
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }, status=status.HTTP_200_OK)
            else:
                # Record the failed attempt
                FailedAttempt.objects.create(ip_address=ip_address, phone_number=phone_number, attempt_type='login')
                return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)


class CompleteProfileView(generics.GenericAPIView):
    serializer_class = UserDetailsSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user.first_name = serializer.validated_data.get('first_name')
            user.last_name = serializer.validated_data.get('last_name')
            user.email = serializer.validated_data.get('email')
            user.save()
            return Response({'detail': 'Profile updated successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
