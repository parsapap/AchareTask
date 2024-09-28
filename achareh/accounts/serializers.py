from rest_framework import serializers
from .models import CustomUser
from .validators import validate_iranian_mobile


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[validate_iranian_mobile])

    def validate_phone_number(self, value):
        # Ensure the phone number is not already in use
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value


class VerifyCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[validate_iranian_mobile])
    password = serializers.CharField()


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")

        return value


class UserDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']

    def validate_email(self, value):
        # Check if email is already in use by another user
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")

        return value

    def update(self, instance, validated_data):
        # Updating user details with validated data
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.save()

        return instance
