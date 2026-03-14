from .models import CriticalProcess


def calc_business_impact(process):
    """Returns a composite impact score 1-5"""
    return round((process.danno_reputazionale + process.danno_normativo + process.danno_operativo) / 3)


def get_unvalidated_processes(plant_id):
    return CriticalProcess.objects.filter(plant_id=plant_id, status="bozza")


def approve_process(process, user):
    from django.utils import timezone

    process.status = "approvato"
    process.approved_by = user
    process.approved_at = timezone.now()
    process.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
