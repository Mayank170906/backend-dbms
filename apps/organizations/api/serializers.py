from rest_framework import serializers

from apps.accounts.api.serializers import UserSerializer
from apps.organizations.models import Membership, Organization, Team


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "description", "owner", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]


class MembershipSerializer(serializers.ModelSerializer):
    # Nested for display (the frontend needs a name, not just an id) — this
    # serializer is only ever used to render a response, never to validate
    # POST input (membership creation is handled by OrganizationService,
    # called directly from the view with plain request.data), so making
    # "user" a read-only nested representation doesn't break writes.
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "organization", "user", "role", "joined_at"]
        read_only_fields = ["id", "organization", "joined_at"]


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "organization", "name", "description", "created_at"]
        read_only_fields = ["id", "created_at"]
