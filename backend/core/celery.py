import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
app = Celery("grc")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-expired-evidences": {
        "task": "apps.controls.tasks.check_expired_evidences",
        "schedule": crontab(hour=2, minute=0),
    },
    "generate-weekly-kpi-snapshots": {
        "task": "apps.reporting.tasks.generate_weekly_kpi_snapshots",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),  # Monday 06:00
    },
    "check-unrevalued-changes": {
        "task": "apps.assets.tasks.check_unrevalued_changes",
        "schedule": crontab(hour=7, minute=0, day_of_week=1),  # Monday 07:00
    },
    "check-software-eos": {
        "task": "apps.assets.tasks.check_software_eos",
        "schedule": crontab(hour=7, minute=15, day_of_week=1),  # Monday 07:15
    },
    "notify-expiring-roles": {
        "task": "apps.governance.tasks.notify_expiring_roles_task",
        "schedule": crontab(hour=8, minute=0),
    },
    "notify-pdca-blocked": {
        "task": "apps.pdca.tasks.notify_blocked_pdca_task",
        "schedule": crontab(hour=8, minute=30),
    },
    "check-expired-bcp-plans": {
        "task": "apps.bcp.tasks.check_expired_bcp_plans",
        "schedule": crontab(hour=2, minute=10),
    },
    "cleanup-audit-logs": {
        "task": "apps.audit_trail.tasks.cleanup_expired_audit_logs",
        "schedule": crontab(hour=3, minute=0, day_of_month=1),
    },
    "cleanup-celery-results": {
        "task": "apps.audit_trail.tasks.cleanup_celery_results",
        "schedule": crontab(hour=3, minute=30),
    },
    "check-upcoming-audits": {
        "task": "apps.audit_prep.tasks.check_upcoming_audits",
        "schedule": crontab(hour=7, minute=30, day_of_week=1),
    },
    "check-overdue-findings": {
        "task": "apps.audit_prep.tasks.check_overdue_findings",
        "schedule": crontab(hour=8, minute=0),
    },
    "check-stale-audit-preps": {
        "task": "apps.audit_prep.tasks.check_stale_audit_preps",
        "schedule": crontab(hour=8, minute=15, day_of_week=1),
    },
    "check-nis2-deadlines": {
        "task": "apps.incidents.tasks.check_nis2_deadlines",
        "schedule": crontab(minute="*/30"),
    },
    "check-final-report-deadlines": {
        "task": "apps.incidents.tasks.check_final_report_deadlines",
        "schedule": crontab(hour=9, minute=0),
    },
    "check-questionnaire-followups": {
        "task": "apps.suppliers.tasks.check_questionnaire_followups_task",
        "schedule": crontab(hour=9, minute=0),
    },
    "recompute-supplier-risk-adj": {
        "task": "apps.suppliers.tasks.recompute_expired_risk_adj_task",
        "schedule": crontab(hour=2, minute=45),  # 02:45 ogni giorno
    },
    "check-schedule-deadlines": {
        "task": "apps.compliance_schedule.tasks.check_schedule_deadlines",
        "schedule": crontab(hour=2, minute=30),  # 02:30 ogni giorno
    },
    "notify-expiring-documents": {
        "task": "apps.documents.tasks.notify_expiring_documents",
        "schedule": crontab(hour=7, minute=45),  # 07:45 ogni giorno
    },
}

