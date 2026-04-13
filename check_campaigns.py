import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.masterdata.models.inventory import inventaire

total = inventaire.objects.count()
print(f'Total inventaires: {total}')
for cat in ['Emplacement', 'Zone', 'Location', 'Departement']:
    count = inventaire.objects.filter(categorie=cat).count()
    print(f'  {cat}: {count}')

if total > 0:
    for inv in inventaire.objects.all()[:5]:
        print(f'  id={inv.id} nom={inv.nom} cat={inv.categorie} statut={inv.statut} user_id={inv.user_id}')
