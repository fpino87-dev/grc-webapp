from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Document, DocumentVersion
from .serializers import DocumentApprovalSerializer, DocumentSerializer, DocumentVersionSerializer
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

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        doc = self.get_object()
        services.submit_for_review(doc, request.user)
        return Response(DocumentSerializer(doc).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        doc = self.get_object()
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


class DocumentVersionViewSet(viewsets.ModelViewSet):
    queryset = DocumentVersion.objects.select_related("document", "uploaded_by")
    serializer_class = DocumentVersionSerializer
    filterset_fields = ["document"]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
