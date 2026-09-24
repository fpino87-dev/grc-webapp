from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("suppliers", "0017_supplier_vat_normalized"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="supplier",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True), models.Q(("vat_normalized", ""), _negated=True)),
                fields=("vat_normalized",),
                name="uniq_supplier_vat_active",
            ),
        ),
    ]
