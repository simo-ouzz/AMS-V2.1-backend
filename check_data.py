import os, sys, django

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_DIR = os.path.join(BASE_DIR, 'apps')
if APPS_DIR not in sys.path:
    sys.path.insert(0, APPS_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from masterdata.models import article, item, tag
print(f"Articles: {article.objects.count()}")
print(f"Items: {item.objects.count()}")
print(f"Tags: {tag.objects.count()}")

from django.urls import resolve
routes = ['/api/detail/user/', '/api/kpi/dashboard/', '/api/user/permissions/', '/api/token/']
for url in routes:
    try:
        r = resolve(url)
        print(f"OK {url} -> {r.func.__name__ if hasattr(r.func, '__name__') else r.func}")
    except Exception as e:
        print(f"FAIL {url} -> {e}")
