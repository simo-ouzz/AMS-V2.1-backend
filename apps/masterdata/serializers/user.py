from rest_framework import serializers
from masterdata.models import UserWeb
from django.contrib.auth.models import Group


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


class UserAdminSerializer(serializers.ModelSerializer):
    compte_id = serializers.IntegerField(source="compte.id", read_only=True)
    compte_label = serializers.CharField(source="compte.libelle", read_only=True, default=None)
    group_ids = serializers.SerializerMethodField()
    group_names = serializers.SerializerMethodField()
    permission_codenames = serializers.SerializerMethodField()

    class Meta:
        model = UserWeb
        fields = [
            "id",
            "nom",
            "prenom",
            "email",
            "role",
            "type",
            "is_active",
            "is_staff",
            "is_superuser",
            "compte",
            "compte_id",
            "compte_label",
            "group_ids",
            "group_names",
            "permission_codenames",
        ]

    def get_group_ids(self, obj):
        return list(obj.groups.values_list("id", flat=True))

    def get_group_names(self, obj):
        return list(obj.groups.values_list("name", flat=True))

    def get_permission_codenames(self, obj):
        perms = set(obj.user_permissions.values_list("codename", flat=True))
        for group in obj.groups.all():
            perms.update(group.permissions.values_list("codename", flat=True))
        return sorted(perms)


class UserAdminCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    group_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        write_only=True,
        allow_empty=True,
    )

    class Meta:
        model = UserWeb
        fields = [
            "nom",
            "prenom",
            "email",
            "role",
            "type",
            "is_active",
            "is_staff",
            "compte",
            "password",
            "group_ids",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        group_ids = validated_data.pop("group_ids", [])
        user = UserWeb(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        if group_ids:
            groups = Group.objects.filter(id__in=group_ids)
            user.groups.set(groups)
        return user


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    group_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        write_only=True,
        allow_empty=True,
    )

    class Meta:
        model = UserWeb
        fields = [
            "nom",
            "prenom",
            "email",
            "role",
            "type",
            "is_active",
            "is_staff",
            "compte",
            "password",
            "group_ids",
        ]
        extra_kwargs = {
            "email": {"required": False},
            "role": {"required": False},
            "nom": {"required": False},
            "prenom": {"required": False},
            "type": {"required": False},
            "is_active": {"required": False},
            "is_staff": {"required": False},
            "compte": {"required": False},
        }

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        group_ids = validated_data.pop("group_ids", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        if group_ids is not None:
            groups = Group.objects.filter(id__in=group_ids)
            instance.groups.set(groups)
        return instance
