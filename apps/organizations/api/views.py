from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.organizations.models import Membership, Organization, Team
from apps.organizations.services import OrganizationService, TeamService

from .permissions import IsOrganizationAdmin
from .serializers import MembershipSerializer, OrganizationSerializer, TeamSerializer

User = get_user_model()


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Organization.objects.none()
        # IDOR protection: an organization the caller doesn't belong to
        # simply isn't in this queryset, so /organizations/<other-org>/
        # 404s instead of leaking whether it exists.
        return Organization.objects.filter(memberships__user=self.request.user).distinct()

    def perform_create(self, serializer):
        organization = OrganizationService.create_organization(
            owner=self.request.user,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
        )
        serializer.instance = organization

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        organization = self.get_object()
        if request.method == "GET":
            queryset = organization.memberships.select_related("user").order_by("user__username")
            page = self.paginate_queryset(queryset)
            serializer = MembershipSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        user = get_object_or_404(User, pk=request.data.get("user_id"))
        role = request.data.get("role", Membership.Role.MEMBER)
        membership = OrganizationService.add_member(organization=organization, user=user, role=role)
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["organization"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Team.objects.none()
        return Team.objects.filter(organization__memberships__user=self.request.user).distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data["organization"]
        if not Membership.objects.filter(organization=organization, user=self.request.user).exists():
            raise PermissionDenied("You are not a member of this organization.")
        team = TeamService.create_team(
            organization=organization,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
        )
        serializer.instance = team
