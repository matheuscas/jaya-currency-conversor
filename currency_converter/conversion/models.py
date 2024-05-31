# type: ignore
from users.models import CustomUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Conversion(models.Model):
    user_id = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="conversions"
    )
    from_currency = models.CharField(max_length=3)
    from_amount = models.DecimalField(_("From Amount"), max_digits=5, decimal_places=2)
    to_currency = models.CharField(max_length=3)
    to_amount = models.DecimalField(_("To Amount"), max_digits=5, decimal_places=2)
    rate = models.DecimalField(_("Rate"), max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(_("Created At"))

    class Meta:
        verbose_name = _("Conversion")
        verbose_name_plural = _("Conversions")

    def __str__(self):
        return self.name
