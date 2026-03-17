from rest_framework import viewsets, status, filters, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse, Http404
from django.core.files.storage import default_storage
import os

from .models import Document, DocumentVersion, Evidence
from .serializers import (
    DocumentApprovalSerializer,
    DocumentSerializer,
    DocumentVersionSerializer,
    EvidenceSerializer,
)
from . import services


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related(
        "plant", "owner", "reviewer", "approver"
    ).prefetch_related("versions")
    serializer_class = DocumentSerializer
    filterset_fields = ["plant", "status", "category", "is_mandatory"]
    search_fields = ["title"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"], url_path="download-latest")
    def download_latest(self, request, pk=None):
        """
        Scarica l'ultima versione approvata/caricata del documento usando default_storage.
        """
        document = self.get_object()
        version = document.versions.first()
        if not version or not version.storage_path:
            raise Http404("Nessun file disponibile per questo documento.")

        if not default_storage.exists(version.storage_path):
            raise Http404("File non trovato nello storage.")

        file_handle = default_storage.open(version.storage_path, "rb")
        filename = version.file_name or os.path.basename(version.storage_path)
        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=filename,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        from apps.governance.services import user_has_document_permission

        doc = self.get_object()
        if not user_has_document_permission(request.user, doc, action="submit"):
            return Response(
                {"detail": "Non hai i permessi per inviare in revisione questo documento."},
                status=status.HTTP_403_FORBIDDEN,
            )
        services.submit_for_review(doc, request.user)
        return Response(DocumentSerializer(doc).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from apps.governance.services import user_has_document_permission

        doc = self.get_object()
        if not user_has_document_permission(request.user, doc, action="approve"):
            return Response(
                {"detail": "Non hai i permessi per approvare questo documento."},
                status=status.HTTP_403_FORBIDDEN,
            )
        services.approve_document(doc, request.user, request.data.get("notes", ""))
        return Response(DocumentSerializer(doc).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        doc = self.get_object()
        services.reject_document(doc, request.user, request.data.get("notes", ""))
        return Response(DocumentSerializer(doc).data)

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        docs = services.get_expiring_documents(
            int(request.query_params.get("days", 30))
        )
        return Response(DocumentSerializer(docs, many=True).data)

    @action(detail=True, methods=["post"], url_path="link-controls")
    def link_controls(self, request, pk=None):
        """
        Collega questo documento a una lista di ControlInstance.
        Body: { "control_instance_ids": ["uuid1", "uuid2"] }
        """
        from apps.controls.models import ControlInstance
        document = self.get_object()
        ids = request.data.get("control_instance_ids", [])
        linked = []
        for cid in ids:
            ci = ControlInstance.objects.filter(pk=cid).first()
            if ci:
                ci.documents.add(document)
                linked.append(str(ci.pk))
        return Response({"ok": True, "linked": linked, "count": len(linked)})

    @action(
        detail=True,
        methods=["post"],
        url_path="upload",
        parser_classes=[parsers.MultiPartParser],
    )
    def upload(self, request, pk=None):
        from django.core.exceptions import ValidationError
        from .services import add_version_with_file
        from .serializers import DocumentVersionSerializer

        document = self.get_object()
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"error": "Nessun file fornito."}, status=status.HTTP_400_BAD_REQUEST)

        change_summary = request.data.get("change_summary", "")
        try:
            version = add_version_with_file(document, uploaded_file, request.user, change_summary)
            serializer = DocumentVersionSerializer(version, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e.message)}, status=status.HTTP_400_BAD_REQUEST)


class DocumentVersionViewSet(viewsets.ModelViewSet):
    queryset = DocumentVersion.objects.select_related("document", "uploaded_by")
    serializer_class = DocumentVersionSerializer
    filterset_fields = ["document"]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class EvidenceViewSet(viewsets.ModelViewSet):
    queryset = Evidence.objects.select_related("plant", "uploaded_by")
    serializer_class = EvidenceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["plant", "evidence_type"]
    search_fields = ["title", "description"]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        qs = super().get_queryset()
        from django.utils import timezone
        expiry = self.request.query_params.get("expiry")
        today = timezone.now().date()
        if expiry == "valide":
            qs = qs.filter(valid_until__gt=today + timezone.timedelta(days=30))
        elif expiry == "in_scadenza":
            qs = qs.filter(valid_until__gte=today, valid_until__lte=today + timezone.timedelta(days=30))
        elif expiry == "scadute":
            qs = qs.filter(valid_until__lt=today)
        return qs

    def create(self, request, *args, **kwargs):
        from django.core.exceptions import ValidationError
        from .services import create_evidence_with_file

        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            try:
                evidence = create_evidence_with_file(request.data, uploaded_file, request.user)
                serializer = self.get_serializer(evidence)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({"error": str(e.message)}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        """
        Scarica il file associato all'evidenza usando default_storage.
        """
        evidence = self.get_object()
        if not evidence.file_path:
            raise Http404("Nessun file associato a questa evidenza.")

        if not default_storage.exists(evidence.file_path):
            raise Http404("File non trovato nello storage.")

        file_handle = default_storage.open(evidence.file_path, "rb")
        filename = os.path.basename(evidence.file_path)
        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=filename,
        )
