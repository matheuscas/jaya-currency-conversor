from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.managers import CustomUserManager
from shortuuid.django_fields import ShortUUIDField


class CustomUser(AbstractUser):
    username = None  # type: ignore
    email = models.EmailField(_("email address"), unique=True)
    external_id = ShortUUIDField(
        unique=True, primary_key=False, max_length=11, editable=False, prefix="user_"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []  # type: ignore

    objects = CustomUserManager()  # type: ignore

    def __str__(self):
        return self.email
