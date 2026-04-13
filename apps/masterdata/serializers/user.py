from rest_framework import serializers
from masterdata.models import UserWeb


class UserLoginSerializer(serializers.Serializer):
    """Authenticate a user by email and password."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = UserWeb.objects.filter(email=attrs.get('email')).first()
        if user:
            if user.check_password(attrs.get('password')):
                return user
            else:
                raise serializers.ValidationError("Mot de passe incorrect.")
        else:
            raise serializers.ValidationError("Aucun utilisateur trouvé avec cet email.")
