import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()

from masterdata.models.inventory import inventaire, inventaire_emplacement
from masterdata.models.asset import item

print(f"Total campaigns: {inventaire.objects.count()}")
print(f"Total items: {item.objects.count()}")

inv = inventaire.objects.first()
if inv:
    print(f"\nCampaign: {inv.nom}")
    tasks = inventaire_emplacement.objects.filter(inventaire=inv).select_related('emplacement')[:5]
    for t in tasks:
        count = item.objects.filter(emplacement_id=t.emplacement_id).count()
        print(f"  {t.emplacement.nom}: {count} expected items")
else:
    print("No campaigns found")
