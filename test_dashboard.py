import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()
from masterdata.views.kpi_dashboard import KPIDashboardAPIView
from rest_framework.test import APIRequestFactory
from masterdata.models import UserWeb
from rest_framework.request import Request
u = UserWeb.objects.get(email='admin@example.com')
f = APIRequestFactory()
r = f.get('/')
r.user = u
v = KPIDashboardAPIView()
resp = v.get(Request(r))
print(json.dumps(resp.data, indent=2, default=str))
