from django.contrib import admin

from .models import Membership, Organization, Team, TeamMembership


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


class TeamInline(admin.TabularInline):
    model = Team
    extra = 0


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "created_at")
    search_fields = ("name", "slug", "owner__username", "owner__email")
    list_filter = ("created_at",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline, TeamInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "organization__name")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "created_at")
    search_fields = ("name", "organization__name")
    inlines = [TeamMembershipInline]


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "joined_at")
    search_fields = ("user__username", "team__name")
