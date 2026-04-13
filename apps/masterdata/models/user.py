from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.models import Group, Permission
from simple_history.models import HistoricalRecords


class Compte(models.Model):
    """Account/tenant to partition data and settings across the platform."""
    libelle = models.CharField(max_length=255)
    code_compte = models.CharField(max_length=255,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.libelle  

class UserWebManager(BaseUserManager):
    """Custom manager used for creating standard users and superusers."""
    def create_user(self, email, role, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, role, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, role, password, **extra_fields)

class UserWeb(AbstractBaseUser, PermissionsMixin, models.Model):  
    """Primary user model for web/mobile with role-based access and groups."""
    ROLES = (
        ('Administrateur', 'Administrateur'),
        ('user', 'User'),
    )
    type = (
        ('web', 'web'),
        ('mobile', 'mobile'),
    )
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length = 255)
    prenom = models.CharField(max_length = 255)
    role = models.CharField(max_length=100, choices=ROLES)
    type = models.CharField(max_length=100, choices=type,default="web")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False,verbose_name='Administrateur',)
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE,blank=True,null=True)
    objects = UserWebManager()
    history = HistoricalRecords()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['role']
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        related_name='user_web_groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        related_name='user_web_permissions'
    )
    def __str__(self):
        return f"{self.prenom} {self.nom}"


    class Meta:
        verbose_name = 'Utilisateur'




class SuperUserProxy(UserWeb):
    """Proxy model used to isolate superusers in the admin interface."""
    class Meta:
        proxy = True
        verbose_name = "Super Utilisateur"
        verbose_name_plural = "Super Utilisateurs"
