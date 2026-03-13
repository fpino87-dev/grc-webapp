from rest_framework.routers import DefaultRouter

from .views import CommitteeMeetingViewSet, RoleAssignmentViewSet, SecurityCommitteeViewSet

router = DefaultRouter()
router.register("role-assignments", RoleAssignmentViewSet, basename="role-assignment")
router.register("committees", SecurityCommitteeViewSet, basename="committee")
router.register("meetings", CommitteeMeetingViewSet, basename="committee-meeting")

urlpatterns = router.urls

