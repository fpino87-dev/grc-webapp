from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection, transaction

User = get_user_model()

TABLES_TO_TRUNCATE = [
    # Audit (prima — ha trigger ma truncate bypassa i vincoli)
    "audit_log",
    "ai_interaction_log",
    # Moduli GRC in ordine di dipendenza (figli prima dei padri)
    "audit_prep_evidenceitem",
    "audit_prep_auditprep",
    "bcp_bcptest",
    "bcp_bcpplan",
    "training_phishingsimulation",
    "training_trainingenrollment",
    "training_trainingcourse",
    "suppliers_supplierassessment",
    "suppliers_supplier",
    "management_review_reviewaction",
    "management_review_managementreview",
    "lessons_lessonlearned",
    "pdca_pdcaphase",
    "pdca_pdcacycle",
    "incidents_rca",
    "incidents_incidentnotification",
    "incidents_incident",
    "tasks_taskcomment",
    "tasks_task",
    "documents_evidence",
    "documents_documentapproval",
    "documents_documentversion",
    "documents_document",
    "risk_riskmitigationplan",
    "risk_riskdimension",
    "risk_riskassessment",
    "bia_risktreamentoption",
    "bia_riskdecision",
    "bia_criticalprocess",
    "assets_assetdependency",
    "assets_assetot",
    "assets_assetit",
    "assets_asset",
    "assets_networkzone",
    "controls_controlinstance",
    "controls_controlmapping",
    "notifications_notificationsubscription",
    "governance_committeemeeting",
    "governance_securitycommittee",
    "governance_roleassignment",
    "auth_grc_externalauditortoken",
    "auth_grc_userplantaccess",
    "plants_plantframework",
    "plants_plant",
    "plants_businessunit",
    # Celery results
    "django_celery_results_taskresult",
    "django_celery_results_groupresult",
    "django_celery_beat_periodictask",
]

# Tabelle che NON vengono mai toccate:
# auth_user, auth_group, auth_permission
# controls_framework, controls_controldomain, controls_control
# django_migrations, django_content_type


class Command(BaseCommand):
    help = "[SOLO TESTING] Reset completo DB — mantiene superuser e framework"

    def add_arguments(self, p):
        p.add_argument(
            "--confirm",
            action="store_true",
            help="Conferma esplicita richiesta per eseguire il reset",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            self.stderr.write(self.style.ERROR(
                "PERICOLOSO: questo comando cancella TUTTI i dati GRC.\n"
                "Usa --confirm per procedere.\n"
                "Es: python manage.py reset_test_db --confirm"
            ))
            return

        # Salva superuser prima del reset
        superusers = list(User.objects.filter(is_superuser=True).values(
            "username", "email", "first_name", "last_name",
            "password", "is_active", "is_staff", "is_superuser",
        ))

        self.stdout.write(f"Superuser salvati: {[u['username'] for u in superusers]}")
        self.stdout.write("Inizio reset...")

        with transaction.atomic():
            with connection.cursor() as cursor:
                # Disabilita temporaneamente i trigger per truncate
                cursor.execute("SET session_replication_role = 'replica';")

                for table in TABLES_TO_TRUNCATE:
                    try:
                        cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE;')
                        self.stdout.write(f"  ✓ {table}")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"  ⚠ {table}: {e}"))

                # Riabilita trigger
                cursor.execute("SET session_replication_role = 'DEFAULT';")

            # Ripristina superuser
            User.objects.filter(is_superuser=False).delete()
            for su in superusers:
                User.objects.get_or_create(
                    username=su["username"],
                    defaults=su,
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nReset completato. "
            f"Superuser ripristinati: {[u['username'] for u in superusers]}\n"
            f"Framework e controlli intatti."
        ))
