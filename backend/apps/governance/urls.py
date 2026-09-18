from rest_framework.routers import DefaultRouter

from .views import (
    CommitteeMemberViewSet,
    DocumentWorkflowPolicyViewSet,
    RoleAssignmentViewSet,
    RoleRequirementViewSet,
    SecurityCommitteeViewSet,
    SecurityObjectiveViewSet,
)

router = DefaultRouter()
router.register("role-assignments", RoleAssignmentViewSet, basename="role-assignment")
router.register("role-requirements", RoleRequirementViewSet, basename="role-requirement")
router.register("document-workflow-policies", DocumentWorkflowPolicyViewSet, basename="document-workflow-policy")
router.register("committees", SecurityCommitteeViewSet, basename="committee")
router.register("committee-members", CommitteeMemberViewSet, basename="committee-member")
router.register("security-objectives", SecurityObjectiveViewSet, basename="security-objective")

urlpatterns = router.urls

        