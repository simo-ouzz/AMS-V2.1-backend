import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()
from masterdata.models import UserWeb
u = UserWeb.objects.get(email='admin@example.com')
u.set_password('adminadmin123')
u.save()
print(f'Password reset OK for {u.email}, role={u.role}, is_superuser={u.is_superuser}')
