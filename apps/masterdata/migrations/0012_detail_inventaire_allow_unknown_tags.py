from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("masterdata", "0011_change_etat_correcte_to_trouvee"),
    ]

    operations = [
        migrations.AlterField(
            model_name="detail_inventaire",
            name="item",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, to="masterdata.item"),
        ),
        migrations.AddField(
            model_name="detail_inventaire",
            name="tag_reference",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
