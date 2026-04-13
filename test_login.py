import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.views import TokenObtainPairView
import json

factory = APIRequestFactory()
request = factory.post('/api/token/', {'email': 'admin@example.com', 'password': 'adminadmin123'}, format='json')
view = TokenObtainPairView.as_view()
response = view(request)
print(f'Status: {response.status_code}')
print(json.dumps(response.data, indent=2, default=str))
