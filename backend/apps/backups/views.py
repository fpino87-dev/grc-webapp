from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.auth_grc.permissions import IsGrcSuperAdmin

from .models import BackupRecord
from .serializers import BackupRecordSerializer
from .services import create_backup, delete_backup, import_backup, start_restore

BACKUP_DIR = Path(getattr(settings, "BACKUP_DIR", "/app/backups"))


class BackupViewSet(ReadOnlyModelViewSet):
    """
    Gestione backup del database. Solo super_admin.

    GET    /api/v1/backups/               → lista backup
    GET    /api/v1/backups/{id}/          → dettaglio
    POST   /api/v1/backups/create/        → avvia backup manuale
    POST   /api/v1/backups/import/        → importa file .dump/.dump.enc (multipart)
    GET    /api/v1/backups/{id}/download/ → scarica file
    POST   /api/v1/backups/{id}/restore/  → ripristina
    DELETE /api/v1/backups/{id}/remove/   → elimina
    """

    queryset = BackupRecord.objects.all()
    serializer_class = BackupRecordSerializer
    permission_classes = [IsGrcSuperAdmin]

    @action(detail=False, methods=["post"], url_path="create")
    def create_backup(self, request):
        record = create_backup(request.user, backup_type="manual")
        return Response(
            BackupRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="import")
    def import_backup(self, request):
        uploaded = request.FILES.get("file")
        if uploaded is None:
            return Response(
                {"detail": "Nessun file caricato: campo multipart 'file' obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            record = import_backup(uploaded, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            BackupRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        record = self.get_object()
        if record.status != BackupRecord.Status.COMPLETED:
            return Response(
                {"detail": "Backup non disponibile per il download."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        filepath = BACKUP_DIR / record.filename
        if not filepath.exists():
            return Response(
                {"detail": "File non trovato sul server."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(
            open(filepath, "rb"),  # noqa: WPS515
            content_type="application/octet-stream",
            as_attachment=True,
            filename=record.filename,
        )

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        # Asincrono (newfix 2026-06-09 #3): pg_restore può superare il timeout
        # gunicorn (120s) — il lavoro avviene su Celery, qui solo l'accodamento.
        # Il client fa polling su GET /backups/{id}/ finché status != restoring.
        record = self.get_object()
        try:
            record = start_restore(record.pk, request.user)
        except (FileNotFoundError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            BackupRecordSerializer(record).data,
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["delete"], url_path="remove")
    def remove(self, request, pk=None):
        record = self.get_object()
        delete_backup(record.pk, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
