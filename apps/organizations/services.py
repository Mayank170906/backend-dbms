from django.db import transaction
from django.utils.text import slugify

from .models import Membership, Organization, Team, TeamMembership


class OrganizationService:
    @staticmethod
    def _unique_slug(name: str) -> str:
        base_slug = slugify(name)[:250] or "organization"
        slug = base_slug
        suffix = 1
        while Organization.objects.filter(slug=slug).exists():
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        return slug

    @classmethod
    @transaction.atomic
    def create_organization(cls, *, owner, name: str, description: str = "") -> Organization:
        # An organization without its owner's OWNER membership row would
        # leave the owner unable to manage the org they just created, so
        # both rows are written in the same transaction.
        organization = Organization.objects.create(
            name=name,
            slug=cls._unique_slug(name),
            description=description,
            owner=owner,
        )
        Membership.objects.create(
            organization=organization,
            user=owner,
            role=Membership.Role.OWNER,
        )
        return organization

    @staticmethod
    @transaction.atomic
    def add_member(*, organization: Organization, user, role: str = Membership.Role.MEMBER) -> Membership:
        membership, _ = Membership.objects.update_or_create(
            organization=organization,
            user=user,
            defaults={"role": role},
        )
        return membership


class TeamService:
    @staticmethod
    def create_team(*, organization: Organization, name: str, description: str = "") -> Team:
        return Team.objects.create(organization=organization, name=name, description=description)

    @staticmethod
    def add_member(*, team: Team, user) -> TeamMembership:
        membership, _ = TeamMembership.objects.get_or_create(team=team, user=user)
        return membership
