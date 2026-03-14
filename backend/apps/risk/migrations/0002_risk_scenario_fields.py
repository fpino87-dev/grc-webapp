from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("risk", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="riskassessment",
            name="name",
            field=models.CharField(max_length=200, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="riskassessment",
            name="threat_category",
            field=models.CharField(max_length=50, blank=True, default="",
                choices=[("accesso_non_autorizzato","Accesso non autorizzato"),("malware_ransomware","Malware / Ransomware"),("data_breach","Data breach / Fuga di dati"),("phishing_social","Phishing / Social engineering"),("guasto_hw_sw","Guasto hardware / software"),("disastro_naturale","Disastro naturale / ambientale"),("errore_umano","Errore umano"),("attacco_supply_chain","Attacco supply chain"),("ddos","DoS / DDoS"),("insider_threat","Insider threat"),("furto_perdita","Furto / perdita dispositivi"),("altro","Altro")]),
        ),
        migrations.AddField(
            model_name="riskassessment",
            name="probability",
            field=models.IntegerField(null=True, blank=True, choices=[(1,"1 – Molto bassa"),(2,"2 – Bassa"),(3,"3 – Media"),(4,"4 – Alta"),(5,"5 – Molto alta")]),
        ),
        migrations.AddField(
            model_name="riskassessment",
            name="impact",
            field=models.IntegerField(null=True, blank=True, choices=[(1,"1 – Trascurabile"),(2,"2 – Minore"),(3,"3 – Moderato"),(4,"4 – Grave"),(5,"5 – Critico")]),
        ),
        migrations.AddField(
            model_name="riskassessment",
            name="treatment",
            field=models.CharField(max_length=20, blank=True, default="", choices=[("mitigare","Mitigare"),("accettare","Accettare"),("trasferire","Trasferire"),("evitare","Evitare")]),
        ),
    ]
