from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("suppliers", "0002_supplierassessment_review_notes_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="supplier",
            old_name="contract_expiry",
            new_name="evaluation_date",
        ),
        migrations.AddField(
            model_name="supplier",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
