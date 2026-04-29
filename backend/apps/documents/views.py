from rest_framework import viewsets, status, filters, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse, Http404
from django.core.files.storage import default_storage
from django.utils.translation import gettext as _
import os

from core.scoping import PlantScopedQuerysetMixin, get_user_plant_ids

from .models import Document, DocumentVersion, Evidence
from .permissions import DocumentPermission
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
    ).prefetch_related("versions", "shared_plants")
    serializer_class = DocumentSerializer
    permission_classes = [DocumentPermission]
    filterset_fields = ["status", "category", "is_mandatory"]
    search_fields = ["title"]

    def get_queryset(self):
        from django.db.models import Q
        qs = super().get_queryset().filter(deleted_at__isnull=True)

        # RBAC plant scoping (S1): un utente vede solo i documenti del proprio
        # plant, condivisi col proprio plant, o org-wide (plant=null).
        plant_ids = get_user_plant_ids(self.request.user)
        if plant_ids is not None:
            if not plant_ids:
                return qs.none()
            qs = qs.filter(
                Q(plant_id__in=plant_ids)
                | Q(shared_plants__in=plant_ids)
                | Q(plant__isnull=True)
            ).distinct()

        plant_id = self.request.query_params.get("plant")
        if plant_id:
            # plant proprietario OPPURE condiviso con questo plant OPPURE org-wide (plant=null)
            qs = qs.filter(
                Q(plant_id=plant_id) | Q(shared_plants=plant_id) | Q(plant__isnull=True)
            ).distinct()
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="share")
    def share(self, request, pk=None):
        """
        Aggiorna la lista dei plant con cui il documento è condiviso.
        Body: { "plant_ids": ["uuid1", "uuid2"] }
        I plant_ids sostituiscono la lista corrente.
        """
        from apps.plants.models import Plant
        from core.audit import log_action

        document = self.get_object()
        plant_ids = request.data.get("plant_ids", [])
        # Escludi il plant proprietario dalla lista shared (non ha senso auto-condividere)
        plants = Plant.objects.filter(pk__in=plant_ids, deleted_at__isnull=True).exclude(
            pk=document.plant_id
        )
        document.shared_plants.set(plants)
        log_action(
            user=request.user,
            action_code="document.shared",
            level="L2",
            entity=document,
            payload={"plant_ids": [str(p.id) for p in plants]},
        )
        return Response({
            "shared_with": [{"id": str(p.id), "name": p.name, "code": p.code} for p in plants]
        })

    def destroy(self, request, *args, **kwargs):
        from django.core.exceptions import ValidationError

        document = self.get_object()
        try:
            services.delete_document(document, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="download-latest")
    def download_latest(self, request, pk=None):
        """
        Scarica l'ultima versione approvata/caricata del documento usando default_storage.
        """
        document = self.get_object()
        version = document.versions.first()
        if not version or not version.storage_path:
            raise Http404("Nessun file disponibile per questo documento.")

        # Prevenzione path traversal: il basename non deve contenere ".."
        storage_path = version.storage_path
        if ".." in storage_path or storage_path.startswith("/"):
            raise Http404("Percorso file non valido.")

        if not default_storage.exists(storage_path):
            raise Http404("File non trovato nello storage.")

        file_handle = default_storage.open(storage_path, "rb")
        # Usa solo il basename per il filename nel Content-Disposition
        filename = os.path.basename(version.file_name or storage_path)
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
                {"detail": _("Non hai i permessi per inviare in revisione questo documento.")},
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
                {"detail": _("Non hai i permessi per approvare questo documento.")},
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
            return Response({"error": _("Nessun file fornito.")}, status=status.HTTP_400_BAD_REQUEST)

        change_summary = request.data.get("change_summary", "")
        try:
            version = add_version_with_file(document, uploaded_file, request.user, change_summary)
            serializer = DocumentVersionSerializer(version, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e.message)}, status=status.HTTP_400_BAD_REQUEST)


class DocumentVersionViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = DocumentVersion.objects.select_related("document", "uploaded_by")
    serializer_class = DocumentVersionSerializer
    permission_classes = [DocumentPermission]
    filterset_fields = ["document"]
    plant_field = "document__plant"
    allow_null_plant = True  # versioni di documenti org-wide visibili a tutti

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class EvidenceViewSet(PlantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Evidence.objects.select_related("plant", "uploaded_by").prefetch_related(
        "control_instances__control__framework"
    )
    serializer_class = EvidenceSerializer
    permission_classes = [DocumentPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["evidence_type"]
    search_fields = ["title", "description"]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]
    plant_field = "plant"
    allow_null_plant = True  # evidenze org-wide (plant=null) visibili a tutti

    def get_queryset(self):
        from django.db.models import Q
        from django.utils import timezone
        qs = super().get_queryset()

        # Filtro sito: include evidenze del sito richiesto + evidenze org-wide (plant=null)
        plant_id = self.request.query_params.get("plant")
        if plant_id:
            qs = qs.filter(Q(plant_id=plant_id) | Q(plant__isnull=True))

        expiry = self.request.query_params.get("expiry")
        today = timezone.now().date()
        if expiry == "valide":
            qs = qs.filter(valid_until__gt=today + timezone.timedelta(days=30))
        elif expiry == "in_scadenza":
            qs = qs.filter(valid_until__gte=today, valid_until__lte=today + timezone.timedelta(days=30))
        elif expiry == "scadute":
            qs = qs.filter(valid_until__lt=today)
        return qs

    def destroy(self, request, *args, **kwargs):
        from django.core.exceptions import ValidationError

        evidence = self.get_object()
        try:
            services.delete_evidence(evidence, request.user)
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0] if getattr(e, "messages", None) else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

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
            raise Http404(_("Nessun file associato a questa evidenza."))

        file_path = evidence.file_path
        if ".." in file_path or file_path.startswith("/"):
            raise Http404(_("Percorso file non valido."))

        if not default_storage.exists(file_path):
            raise Http404(_("File non trovato nello storage."))

        file_handle = default_storage.open(file_path, "rb")
        filename = os.path.basename(file_path)
        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=filename,
        )
