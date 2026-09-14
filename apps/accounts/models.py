from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Custom user model from the start: swapping AUTH_USER_MODEL after the
    # first migration touches every FK to auth.User, so it's set up now even
    # though this only adds a few fields beyond AbstractUser.
    email = models.EmailField("email address", unique=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.username
