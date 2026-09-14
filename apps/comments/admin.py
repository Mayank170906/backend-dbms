from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("body", "task__title", "author__username")
