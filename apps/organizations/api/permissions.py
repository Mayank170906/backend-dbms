from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.organizations.models import Membership


class IsOrganizationAdmin(BasePermission):
    """Any member may read; only OWNER/ADMIN may write.

    Object-level only — get_queryset() on the view already restricts the
    queryset to organizations the user belongs to, so a non-member never
    reaches has_object_permission() for an org they have no standing in
    (they get a 404, not a 403, avoiding an existence-leak via status code).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return Membership.objects.filter(organization=obj, user=request.user).exists()
        return Membership.objects.filter(
            organization=obj,
            user=request.user,
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
        ).exists()
