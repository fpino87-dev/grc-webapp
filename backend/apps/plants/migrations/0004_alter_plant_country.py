from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plants", "0003_alter_plant_logo_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plant",
            name="country",
            field=models.CharField(
                choices=[
                    ("AT", "Austria"),
                    ("BE", "Belgio"),
                    ("BG", "Bulgaria"),
                    ("CY", "Cipro"),
                    ("CZ", "Repubblica Ceca"),
                    ("DE", "Germania"),
                    ("DK", "Danimarca"),
                    ("EE", "Estonia"),
                    ("ES", "Spagna"),
                    ("FI", "Finlandia"),
                    ("FR", "Francia"),
                    ("GR", "Grecia"),
                    ("HR", "Croazia"),
                    ("HU", "Ungheria"),
                    ("IE", "Irlanda"),
                    ("IT", "Italia"),
                    ("LT", "Lituania"),
                    ("LU", "Lussemburgo"),
                    ("LV", "Lettonia"),
                    ("MT", "Malta"),
                    ("NL", "Paesi Bassi"),
                    ("PL", "Polonia"),
                    ("PT", "Portogallo"),
                    ("RO", "Romania"),
                    ("SE", "Svezia"),
                    ("SI", "Slovenia"),
                    ("SK", "Slovacchia"),
                    ("GB", "Regno Unito"),
                    ("NO", "Norvegia"),
                    ("CH", "Svizzera"),
                    ("TR", "Turchia"),
                    ("US", "Stati Uniti"),
                    ("JP", "Giappone"),
                    ("CN", "Cina"),
                    ("OTHER", "Altro"),
                ],
                default="IT",
                help_text="Paese del sito — determina il CSIRT NIS2 competente",
                max_length=10,
            ),
        ),
    ]
