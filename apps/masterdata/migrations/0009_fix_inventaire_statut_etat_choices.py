from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("masterdata", "0008_seed_type_tags"),
    ]

    operations = [
        # Fix inventaire_emplacement.statut: typo in choices key + lowercase default
        migrations.AlterField(
            model_name="inventaire_emplacement",
            name="statut",
            field=models.CharField(
                choices=[
                    ("Terminer", "Terminer"),
                    ("En attente", "En attente"),
                    ("En cours", "En cours"),
                ],
                default="En attente",
                max_length=255,
            ),
        ),
        # Add choices constraint to detail_inventaire.etat
        migrations.AlterField(
            model_name="detail_inventaire",
            name="etat",
            field=models.CharField(
                choices=[
                    ("correcte", "correcte"),
                    ("intru", "intru"),
                    ("manquant", "manquant"),
                    ("inconnu", "inconnu"),
                    ("non_affecter", "non_affecter"),
                ],
                max_length=255,
            ),
        ),
    ]
